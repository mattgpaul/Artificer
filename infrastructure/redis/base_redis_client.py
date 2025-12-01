"""Redis client base class with namespacing and connection management.

This module provides the BaseRedisClient abstract class for Redis operations
with automatic key namespacing, connection pooling and health checks.
Pattern-specific helpers (queues, streams, pub/sub, locks, KV, etc.) are
implemented in dedicated clients that compose this base.
"""

import time
from abc import abstractmethod
from typing import Protocol

import redis

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger


class MetricsRecorder(Protocol):
    """Lightweight protocol for recording metrics.

    Concrete implementations can integrate with Prometheus, StatsD, etc.
    """

    def incr(
        self,
        name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter."""
        ...

    def observe(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a timing/measurement."""
        ...


class BaseRedisClient(Client):
    """Base class for Redis client operations with connection pooling.

    Provides connection management, namespace isolation, and common Redis
    operations for all Redis-based data brokers. Handles connection pooling,
    key building with namespace prefixes, and comprehensive error handling.

    Attributes:
        logger: Configured logger instance.
        namespace: Redis key namespace for this client.
        host: Redis server hostname from environment.
        port: Redis server port from environment.
        db: Redis database number from environment.
        max_connections: Maximum connection pool size.
        socket_timeout: Socket timeout in seconds.
        pool: Redis connection pool instance.
        client: Redis client instance.
    """

    def __init__(self, config=None, metrics: MetricsRecorder | None = None):
        """Initialize Redis client with connection pool and configuration.

        Args:
            config: Optional RedisConfig object. If None, auto-populates from environment.
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()
        self.metrics = metrics

        # Auto-populate from environment if not provided
        if config is None:
            from infrastructure.config import RedisConfig  # noqa: PLC0415

            config = RedisConfig()

        # Use config values (either provided or from environment)
        self.host = config.host
        self.port = config.port
        self.db = config.db
        self.max_connections = config.max_connections
        self.socket_timeout = config.socket_timeout

        self._create_connection_pool()

    @abstractmethod
    def _get_namespace(self) -> str:
        """Inheriting class needs to define their db namespace."""
        pass

    def _create_connection_pool(self):
        """Create Redis connection pool with configurable settings."""
        try:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
            )
            self.client = redis.Redis(connection_pool=self.pool)
            self.logger.debug(
                f"Redis connection pool created for namespace: {self.namespace} "
                f"(host: {self.host}, port: {self.port}, db: {self.db})"
            )
        except Exception as e:
            self.logger.error(f"Failed to create Redis connection pool {e}")
            raise

    def _build_key(self, key: str) -> str:
        """Build namsepace key: namespace:key."""
        return f"{self.namespace}:{key}"

    def ping(self) -> bool:
        try:
            start = time.monotonic()
            result = self.client.ping()
            elapsed_ms = (time.monotonic() - start) * 1000

            self.logger.debug(f"PING -> {result}")

            if self.metrics:
                tags = {"namespace": self.namespace}
                metric_base = "redis.ping"
                if result:
                    self.metrics.incr(f"{metric_base}.success", tags=tags)
                else:
                    self.metrics.incr(f"{metric_base}.failure", tags=tags)
                self.metrics.observe(f"{metric_base}.latency_ms", elapsed_ms, tags=tags)

            return result
        except Exception as e:
            self.logger.error(f"Redis ping failed: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.ping.error",
                    tags={"namespace": self.namespace},
                )
            return False

    def close(self):
        """Close the Redis connection pool."""
        if not self.client:
            self.logger.warning("Redis client not initialized, skipping close")
            return
        try:
            self.client.close()
            self.pool.disconnect()
            self.logger.debug(f"Redis connection pool closed for namespace: {self.namespace}")
        except Exception as e:
            self.logger.error(f"Failed to close Redis connection pool: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
