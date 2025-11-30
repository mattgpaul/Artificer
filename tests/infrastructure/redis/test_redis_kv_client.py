"""Unit tests / contract tests for the RedisKVClient.

These tests define the expected behavior of a dedicated key–value client built
on top of `BaseRedisClient`.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest


@pytest.mark.unit
class TestRedisKVClient:
    """Contract tests for a dedicated KV Redis client."""

    def test_set_uses_namespaced_key_and_sets_ttl_when_provided(
        self,
        redis_mocks: Dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`set` should set a namespaced key with TTL when requested."""
        redis_mocks["client"].set.return_value = True

        result = redis_kv_client.set("config", "value", ttl=60)

        assert result is True
        redis_mocks["client"].set.assert_called_once_with(
            "test_namespace:config",
            "value",
            ex=60,
        )

    def test_set_without_ttl_does_not_set_expiration(
        self,
        redis_mocks: Dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`set` without TTL should not set expiration."""
        redis_mocks["client"].set.return_value = True

        result = redis_kv_client.set("config", "value")

        assert result is True
        redis_mocks["client"].set.assert_called_once_with(
            "test_namespace:config",
            "value",
            ex=None,
        )

    def test_set_returns_false_and_logs_on_exception(
        self,
        redis_mocks: Dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`set` should catch errors, log, and return False."""
        redis_mocks["client"].set.side_effect = Exception("Redis error")

        result = redis_kv_client.set("config", "value", ttl=60)

        assert result is False
        redis_mocks["logger"].error.assert_called()

    def test_get_returns_decoded_value_when_present(
        self,
        redis_mocks: Dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`get` should namespace keys and decode bytes to str."""
        redis_mocks["client"].get.return_value = b"value"

        result = redis_kv_client.get("config")

        assert result == "value"
        redis_mocks["client"].get.assert_called_once_with("test_namespace:config")

    def test_get_returns_none_when_key_missing(
        self,
        redis_mocks: Dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`get` should return None when the key does not exist."""
        redis_mocks["client"].get.return_value = None

        result = redis_kv_client.get("config")

        assert result is None

    def test_get_logs_and_returns_none_on_exception(
        self,
        redis_mocks: Dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`get` should catch errors, log, and return None."""
        redis_mocks["client"].get.side_effect = Exception("Redis error")

        result = redis_kv_client.get("config")

        assert result is None
        redis_mocks["logger"].error.assert_called()


