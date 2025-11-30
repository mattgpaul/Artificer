"""Unit tests for the Redis BaseRedisClient infrastructure component.

These tests define the desired contract for a *slim* `BaseRedisClient` that is
responsible only for:

- Connection management and configuration
- Key namespacing
- Basic health checks (`ping`)

Higher-level Redis patterns (queues, streams, pub/sub, locks, etc.) are
intentionally *not* part of this base and are covered by dedicated clients.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest


@pytest.mark.unit
class TestBaseRedisClientCore:
    """Test the core responsibilities of BaseRedisClient."""

    def test_initializes_connection_pool_and_client(
        self,
        redis_mocks: Dict[str, Any],
        base_redis_client,
    ) -> None:
        """Base client should create a connection pool and Redis client."""
        client = base_redis_client

        assert client.namespace == "test_namespace"  # type: ignore[attr-defined]

        # These are already patched by the redis_mocks fixture; we assert the
        # stored attributes match what the fixture created.
        assert client.pool is redis_mocks["pool"]
        assert client.client is redis_mocks["client"]

    def test_build_key_prefixes_namespace(
        self,
        redis_mocks: Dict[str, Any],
        base_redis_client,
    ) -> None:
        """_build_key should consistently prefix keys with the namespace."""
        client = base_redis_client

        assert client._build_key("orders") == "test_namespace:orders"
        assert client._build_key("lock:job") == "test_namespace:lock:job"

    def test_ping_delegates_to_underlying_client(
        self,
        redis_mocks: Dict[str, Any],
        base_redis_client,
    ) -> None:
        """ping should delegate to the underlying Redis client."""
        redis_mocks["client"].ping.return_value = True
        client = base_redis_client

        assert client.ping() is True
        redis_mocks["client"].ping.assert_called_once_with()

    def test_base_client_does_not_expose_high_level_helpers(
        self,
        redis_mocks: Dict[str, Any],
        base_redis_client,
    ) -> None:
        """Base client should NOT provide pattern-specific helper methods.

        These higher-level operations belong in dedicated pattern clients.
        The current implementation still exposes many of these, so this test
        is expected to fail until the refactor is complete.
        """
        client = base_redis_client

        forbidden_methods = [
            # Data-structure helpers
            "get",
            "set",
            "hget",
            "hset",
            "hgetall",
            "hmset",
            "hdel",
            "get_json",
            "set_json",
            "sadd",
            "smembers",
            "srem",
            "sismember",
            "scard",
            "lpush",
            "rpush",
            "lpop",
            "rpop",
            "llen",
            "lrange",
            "exists",
            "delete",
            "expire",
            "ttl",
            "keys",
            "flushdb",
            # Concurrency / pipelines
            "acquire_lock",
            "release_lock",
            "pipeline_execute",
        ]

        for name in forbidden_methods:
            assert not hasattr(
                client,
                name,
            ), f"BaseRedisClient should not expose high-level helper '{name}'"


