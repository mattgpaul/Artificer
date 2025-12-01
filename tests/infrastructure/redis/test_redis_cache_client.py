"""Unit tests / contract tests for RedisCacheClient cache operations.

These tests define the expected behavior of the unified RedisCacheClient for:
- plain string key/value operations via ``get`` / ``set``
- JSON-encoded value operations via ``get_json`` / ``set_json``

All external Redis interactions are mocked via fixtures in ``conftest.py``.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.unit
class TestRedisCacheClientKV:
    """Contract tests for KV operations on RedisCacheClient."""

    def test_set_uses_namespaced_key_and_sets_ttl_when_provided(
        self,
        redis_mocks: dict[str, Any],
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
        redis_mocks: dict[str, Any],
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
        redis_mocks: dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`set` should catch errors, log, and return False."""
        redis_mocks["client"].set.side_effect = Exception("Redis error")

        result = redis_kv_client.set("config", "value", ttl=60)

        assert result is False
        redis_mocks["logger"].error.assert_called()

    def test_get_returns_decoded_value_when_present(
        self,
        redis_mocks: dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`get` should namespace keys and decode bytes to str."""
        redis_mocks["client"].get.return_value = b"value"

        result = redis_kv_client.get("config")

        assert result == "value"
        redis_mocks["client"].get.assert_called_once_with("test_namespace:config")

    def test_get_returns_none_when_key_missing(
        self,
        redis_mocks: dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`get` should return None when the key does not exist."""
        redis_mocks["client"].get.return_value = None

        result = redis_kv_client.get("config")

        assert result is None

    def test_get_logs_and_returns_none_on_exception(
        self,
        redis_mocks: dict[str, Any],
        redis_kv_client,
    ) -> None:
        """`get` should catch errors, log, and return None."""
        redis_mocks["client"].get.side_effect = Exception("Redis error")

        result = redis_kv_client.get("config")

        assert result is None
        redis_mocks["logger"].error.assert_called()

    def test_get_and_set_emit_metrics_when_present(
        self,
        redis_mocks: dict[str, Any],
        redis_kv_client,
        redis_metrics,
    ) -> None:
        """`get`/`set` should emit metrics when a recorder is attached."""
        redis_mocks["client"].set.return_value = True
        redis_mocks["client"].get.return_value = b"value"
        redis_kv_client.metrics = redis_metrics  # type: ignore[attr-defined]

        assert redis_kv_client.set("config", "value", ttl=60) is True
        assert redis_kv_client.get("config") == "value"

        redis_metrics.incr.assert_any_call(
            "redis.kv.set.success",
            tags={"namespace": "test_namespace", "key": "config"},
        )
        redis_metrics.incr.assert_any_call(
            "redis.kv.get.hit",
            tags={"namespace": "test_namespace", "key": "config"},
        )


@pytest.mark.unit
class TestRedisCacheClientJSON:
    """Contract tests for JSON operations on RedisCacheClient."""

    def test_set_json_uses_namespaced_key_and_sets_ttl_when_provided(
        self,
        redis_mocks: dict[str, Any],
        redis_json_client,
    ) -> None:
        """`set_json` should set a namespaced key with TTL when requested."""
        redis_mocks["client"].set.return_value = True

        result = redis_json_client.set_json("config", {"a": 1}, ttl=60)

        assert result is True
        # The exact payload is JSON; we assert the key / ex and leave value as ANY.
        args, kwargs = redis_mocks["client"].set.call_args
        assert args[0] == "test_namespace:config"
        assert kwargs["ex"] == 60

    def test_set_json_without_ttl_does_not_set_expiration(
        self,
        redis_mocks: dict[str, Any],
        redis_json_client,
    ) -> None:
        """`set_json` without TTL should not set expiration."""
        redis_mocks["client"].set.return_value = True

        result = redis_json_client.set_json("config", {"a": 1})

        assert result is True
        args, kwargs = redis_mocks["client"].set.call_args
        assert args[0] == "test_namespace:config"
        assert kwargs["ex"] is None

    def test_set_json_returns_false_and_logs_on_exception(
        self,
        redis_mocks: dict[str, Any],
        redis_json_client,
    ) -> None:
        """`set_json` should catch errors, log, and return False."""
        redis_mocks["client"].set.side_effect = Exception("Redis error")

        result = redis_json_client.set_json("config", {"a": 1}, ttl=60)

        assert result is False
        redis_mocks["logger"].error.assert_called()

    def test_get_json_returns_deserialized_value_when_present(
        self,
        redis_mocks: dict[str, Any],
        redis_json_client,
    ) -> None:
        """`get_json` should namespace keys, decode bytes, and parse JSON."""
        redis_mocks["client"].get.return_value = b'{"a": 1}'

        result = redis_json_client.get_json("config")

        assert result == {"a": 1}
        redis_mocks["client"].get.assert_called_once_with("test_namespace:config")

    def test_get_json_returns_none_when_key_missing(
        self,
        redis_mocks: dict[str, Any],
        redis_json_client,
    ) -> None:
        """`get_json` should return None when the key does not exist."""
        redis_mocks["client"].get.return_value = None

        result = redis_json_client.get_json("config")

        assert result is None

    def test_get_json_logs_and_returns_none_on_invalid_json(
        self,
        redis_mocks: dict[str, Any],
        redis_json_client,
    ) -> None:
        """`get_json` should catch decode errors, log, and return None."""
        redis_mocks["client"].get.return_value = b"not-json"

        result = redis_json_client.get_json("config")

        assert result is None
        redis_mocks["logger"].error.assert_called()

    def test_get_json_and_set_json_emit_metrics_when_present(
        self,
        redis_mocks: dict[str, Any],
        redis_json_client,
        redis_metrics,
    ) -> None:
        """`get_json`/`set_json` should emit metrics when a recorder is attached."""
        redis_mocks["client"].set.return_value = True
        redis_mocks["client"].get.return_value = b'{"a": 1}'
        redis_json_client.metrics = redis_metrics  # type: ignore[attr-defined]

        assert redis_json_client.set_json("config", {"a": 1}, ttl=60) is True
        assert redis_json_client.get_json("config") == {"a": 1}

        redis_metrics.incr.assert_any_call(
            "redis.json.set.success",
            tags={"namespace": "test_namespace", "key": "config"},
        )
        redis_metrics.incr.assert_any_call(
            "redis.json.get.hit",
            tags={"namespace": "test_namespace", "key": "config"},
        )


