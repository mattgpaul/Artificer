"""Unit tests / contract tests for the RedisQueueClient.

These tests define the expected behavior of a dedicated queue client built
on top of `BaseRedisClient`. They are currently marked xfail until the
implementation is provided.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest


@pytest.mark.unit
class TestRedisQueueClient:
    """Contract tests for a dedicated queue Redis client."""

    def test_enqueue_uses_rpush_and_sets_ttl_when_provided(
        self,
        redis_mocks: Dict[str, Any],
        redis_queue_client,
    ) -> None:
        """`enqueue` should push to the queue tail and set TTL when requested."""
        redis_mocks["client"].rpush.return_value = 1

        result = redis_queue_client.enqueue("jobs", "job-1", ttl=60)

        assert result is True
        redis_mocks["client"].rpush.assert_called_once_with(
            "test_namespace:jobs",
            "job-1",
        )
        redis_mocks["client"].expire.assert_called_once_with(
            "test_namespace:jobs",
            60,
        )

    def test_enqueue_returns_false_on_failure(
        self,
        redis_mocks: Dict[str, Any],
        redis_queue_client,
    ) -> None:
        """`enqueue` should return False when the underlying push fails."""
        redis_mocks["client"].rpush.return_value = 0

        result = redis_queue_client.enqueue("jobs", "job-1")

        assert result is False

    def test_dequeue_non_blocking_uses_lpop_and_decodes(
        self,
        redis_mocks: Dict[str, Any],
        redis_queue_client,
    ) -> None:
        """Non-blocking `dequeue` should use LPOP and decode bytes."""
        redis_mocks["client"].lpop.return_value = b"job-1"

        result = redis_queue_client.dequeue("jobs", timeout=None)

        assert result == "job-1"
        redis_mocks["client"].lpop.assert_called_once_with("test_namespace:jobs")

    def test_dequeue_blocking_uses_blpop_when_timeout_provided(
        self,
        redis_mocks: Dict[str, Any],
        redis_queue_client,
    ) -> None:
        """Blocking `dequeue` should use BLPOP with the given timeout."""
        # Redis BLPOP returns a list/tuple of (key, value)
        redis_mocks["client"].blpop.return_value = [
            b"test_namespace:jobs",
            b"job-1",
        ]

        result = redis_queue_client.dequeue("jobs", timeout=5)

        assert result == "job-1"
        redis_mocks["client"].blpop.assert_called_once_with(
            ["test_namespace:jobs"],
            timeout=5,
        )

    def test_dequeue_returns_none_when_queue_empty(
        self,
        redis_mocks: Dict[str, Any],
        redis_queue_client,
    ) -> None:
        """`dequeue` should return None when the queue is empty."""
        redis_mocks["client"].lpop.return_value = None

        result = redis_queue_client.dequeue("jobs", timeout=None)

        assert result is None


