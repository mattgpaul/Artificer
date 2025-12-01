"""Redis key-value client implementation.

This module provides a Redis client for key-value operations including
get and set operations with optional TTL support.
"""

from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisKVClient(BaseRedisClient):
    """Redis key-value client for simple get/set operations.

    Provides methods for storing and retrieving string values with optional
    TTL (time-to-live) support.
    """

    def get(self, key_id: str):
        """Retrieve a value by key.

        Args:
            key_id: The key identifier to retrieve.

        Returns:
            The decoded string value if found, None otherwise.
        """
        key = self._build_key(key_id)
        try:
            raw = self.client.get(key)
            if raw is None:
                if self.metrics:
                    self.metrics.incr(
                        "redis.kv.get.miss",
                        tags={"namespace": self.namespace, "key": key_id},
                    )
                return None

            if isinstance(raw, bytes):
                value = raw.decode("utf-8")
            else:
                value = str(raw)

            self.logger.debug(f"Got value for {key}")

            if self.metrics:
                self.metrics.incr(
                    "redis.kv.get.hit",
                    tags={"namespace": self.namespace, "key": key_id},
                )

            return value
        except Exception as e:
            self.logger.error(f"Failed to retrieve {key}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.kv.get.error",
                    tags={"namespace": self.namespace, "key": key_id},
                )
            return None

    def set(self, key_id: str, value: str, ttl: int | None = None) -> bool:
        """Set a key-value pair with optional TTL.

        Args:
            key_id: The key identifier to set.
            value: The string value to store.
            ttl: Optional time-to-live in seconds.

        Returns:
            True if the operation succeeded, False otherwise.
        """
        key = self._build_key(key_id)
        try:
            result = self.client.set(key, value, ex=ttl)
            self.logger.debug(f"Set {key}:{value}")

            if self.metrics:
                tags = {"namespace": self.namespace, "key": key_id}
                metric_base = "redis.kv.set"
                if result:
                    self.metrics.incr(f"{metric_base}.success", tags=tags)
                else:
                    self.metrics.incr(f"{metric_base}.failure", tags=tags)

            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to set {value} for {key_id}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.kv.set.error",
                    tags={"namespace": self.namespace, "key": key_id},
                )
            return False
