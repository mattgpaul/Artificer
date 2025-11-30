"""Unit / contract tests for the RedisLockClient.

These tests define the expected behavior of a dedicated distributed lock client
built on top of `BaseRedisClient`.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import ANY

import pytest


@pytest.mark.unit
class TestRedisLockClient:
    """Contract tests for a dedicated Redis-based lock client."""

    def test_acquire_lock_uses_namespaced_lock_key_and_sets_ttl(
        self,
        redis_mocks: Dict[str, Any],
        redis_lock_client,
    ) -> None:
        """`acquire_lock` should set a namespaced lock key with NX + TTL."""
        redis_mocks["client"].set.return_value = True

        token = redis_lock_client.acquire_lock("orders", ttl=60)

        assert token is not None
        redis_mocks["client"].set.assert_called_once_with(
            "test_namespace:lock:orders",
            ANY,
            ex=60,
            nx=True,
        )

    def test_acquire_lock_returns_none_when_lock_already_held(
        self,
        redis_mocks: Dict[str, Any],
        redis_lock_client,
    ) -> None:
        """If `SET NX` fails, `acquire_lock` should return None."""
        redis_mocks["client"].set.return_value = False

        token = redis_lock_client.acquire_lock("orders", ttl=60)

        assert token is None

    def test_acquire_lock_logs_and_returns_none_on_exception(
        self,
        redis_mocks: Dict[str, Any],
        redis_lock_client,
    ) -> None:
        """`acquire_lock` should catch errors, log, and return None."""
        redis_mocks["client"].set.side_effect = Exception("Redis error")

        token = redis_lock_client.acquire_lock("orders", ttl=60)

        assert token is None
        redis_mocks["logger"].error.assert_called()

    def test_release_lock_uses_lua_script_and_deletes_on_match(
        self,
        redis_mocks: Dict[str, Any],
        redis_lock_client,
    ) -> None:
        """`release_lock` should use a Lua script to safely delete the lock."""
        redis_mocks["client"].eval.return_value = 1

        result = redis_lock_client.release_lock("orders", token="abc123")

        assert result is True
        # Verify we call EVAL with one key, the namespaced lock key, and the token.
        assert redis_mocks["client"].eval.call_count == 1
        script, num_keys, key, token = redis_mocks["client"].eval.call_args[0]
        assert isinstance(script, str)
        assert num_keys == 1
        assert key == "test_namespace:lock:orders"
        assert token == "abc123"

    def test_release_lock_returns_false_when_script_reports_no_delete(
        self,
        redis_mocks: Dict[str, Any],
        redis_lock_client,
    ) -> None:
        """If the script returns 0, the lock was not released."""
        redis_mocks["client"].eval.return_value = 0

        result = redis_lock_client.release_lock("orders", token="abc123")

        assert result is False

    def test_release_lock_logs_and_returns_false_on_exception(
        self,
        redis_mocks: Dict[str, Any],
        redis_lock_client,
    ) -> None:
        """`release_lock` should catch errors, log, and return False."""
        redis_mocks["client"].eval.side_effect = Exception("Redis error")

        result = redis_lock_client.release_lock("orders", token="abc123")

        assert result is False
        redis_mocks["logger"].error.assert_called()

    def test_acquire_and_release_emit_metrics_when_present(
        self,
        redis_mocks: Dict[str, Any],
        redis_lock_client,
        redis_metrics,
    ) -> None:
        """`acquire_lock` and `release_lock` should emit metrics when enabled."""
        redis_mocks["client"].set.return_value = True
        redis_mocks["client"].eval.return_value = 1
        redis_lock_client.metrics = redis_metrics  # type: ignore[attr-defined]

        token = redis_lock_client.acquire_lock("orders", ttl=60)
        assert token is not None

        assert redis_lock_client.release_lock("orders", token=token) is True

        redis_metrics.incr.assert_any_call(
            "redis.lock.acquire.success",
            tags={"namespace": "test_namespace", "lock": "orders"},
        )
        redis_metrics.incr.assert_any_call(
            "redis.lock.release.success",
            tags={"namespace": "test_namespace", "lock": "orders"},
        )


