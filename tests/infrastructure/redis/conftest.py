"""Shared fixtures for Redis infrastructure tests.

All external Redis interactions are mocked so tests can run without a real
Redis server. Fixtures here are reused across all Redis client tests.
"""

from __future__ import annotations

from typing import Any, Dict

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.redis.base_redis_client import BaseRedisClient
from infrastructure.redis.redis_pub_sub_client import RedisPubSubClient
from infrastructure.redis.redis_queue_client import RedisQueueClient
from infrastructure.redis.redis_stream_client import RedisStreamClient
from infrastructure.redis.redis_kv_client import RedisKVClient

@pytest.fixture
def redis_mocks() -> Dict[str, Any]:
    """Mock the `redis` client and logger used by the Redis base client.

    Provides:
    - redis_module: patched low-level `redis` module
    - pool: mocked ConnectionPool instance
    - client: mocked Redis client instance
    - logger: mocked logger instance
    """
    with patch("infrastructure.redis.base_redis_client.redis") as mock_redis_module, patch(
        "infrastructure.redis.base_redis_client.get_logger",
    ) as mock_get_logger:
        mock_pool = MagicMock()
        mock_client = MagicMock()

        mock_redis_module.ConnectionPool.return_value = mock_pool
        mock_redis_module.Redis.return_value = mock_client

        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        yield {
            "redis_module": mock_redis_module,
            "pool": mock_pool,
            "client": mock_client,
            "logger": mock_logger_instance,
        }


class _TestBaseRedisClient(BaseRedisClient):
    """Concrete BaseRedisClient used only for tests.

    Provides a fixed namespace so contracts around key building and connection
    wiring can be asserted without coupling tests to production namespaces.
    """

    def _get_namespace(self) -> str:
        return "test_namespace"


class _TestRedisPubSubClient(RedisPubSubClient):
    """Concrete RedisPubSubClient with a fixed test namespace."""

    def _get_namespace(self) -> str:
        return "test_namespace"


class _TestRedisQueueClient(RedisQueueClient):
    """Concrete RedisQueueClient with a fixed test namespace."""

    def _get_namespace(self) -> str:
        return "test_namespace"


class _TestRedisStreamClient(RedisStreamClient):
    """Concrete RedisStreamClient with a fixed test namespace."""

    def _get_namespace(self) -> str:
        return "test_namespace"


class _TestRedisKVClient(RedisKVClient):
    """Concrete RedisKVClient with a fixed test namespace."""

    def _get_namespace(self) -> str:
        return "test_namespace"


@pytest.fixture
def base_redis_client(redis_mocks: Dict[str, Any]) -> BaseRedisClient:
    """Provide a fully-wired BaseRedisClient instance for contract tests."""
    return _TestBaseRedisClient()


@pytest.fixture
def redis_pub_sub_client(redis_mocks: Dict[str, Any]) -> RedisPubSubClient:
    """Provide a concrete pub/sub client with a known namespace."""
    return _TestRedisPubSubClient()


@pytest.fixture
def redis_queue_client(redis_mocks: Dict[str, Any]) -> RedisQueueClient:
    """Provide a concrete queue client with a known namespace."""
    return _TestRedisQueueClient()


@pytest.fixture
def redis_stream_client(redis_mocks: Dict[str, Any]) -> RedisStreamClient:
    """Provide a concrete stream client with a known namespace."""
    return _TestRedisStreamClient()


@pytest.fixture
def redis_kv_client(redis_mocks: Dict[str, Any]) -> RedisKVClient:
    """Provide a concrete KV client with a known namespace."""
    return _TestRedisKVClient()


