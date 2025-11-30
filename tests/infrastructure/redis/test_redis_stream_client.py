"""Unit tests / contract tests for the RedisStreamClient.

These tests define the expected behavior of a dedicated streams client built
on top of `BaseRedisClient`. They are currently marked xfail until the
implementation is provided.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

from infrastructure.redis.redis_stream_client import RedisStreamClient


@pytest.mark.unit
class TestRedisStreamClient:
    """Contract tests for a dedicated streams Redis client."""

    @pytest.mark.xfail(
        reason="RedisStreamClient.add_event has not been fully implemented yet.",
        strict=False,
    )
    def test_add_event_uses_xadd_with_namespaced_stream(
        self,
        redis_mocks: Dict[str, Any],
    ) -> None:
        """`add_event` should append to a namespaced stream and return the entry ID."""
        redis_mocks["client"].xadd.return_value = "123-0"
        client = RedisStreamClient()

        event_id = client.add_event("prices", {"symbol": "AAPL", "price": "100"})

        assert event_id == "123-0"
        redis_mocks["client"].xadd.assert_called_once_with(
            "test_namespace:prices",
            {"symbol": "AAPL", "price": "100"},
            id="*",
        )

    @pytest.mark.xfail(
        reason="RedisStreamClient.add_event error handling has not been implemented yet.",
        strict=False,
    )
    def test_add_event_returns_none_on_exception(
        self,
        redis_mocks: Dict[str, Any],
    ) -> None:
        """`add_event` should log and return None when xadd fails."""
        redis_mocks["client"].xadd.side_effect = Exception("Redis error")
        client = RedisStreamClient()

        event_id = client.add_event("prices", {"symbol": "AAPL"})

        assert event_id is None
        redis_mocks["logger"].error.assert_called()

    @pytest.mark.xfail(
        reason="RedisStreamClient.read_events has not been fully implemented yet.",
        strict=False,
    )
    def test_read_events_uses_xread_with_namespaced_stream_and_last_id(
        self,
        redis_mocks: Dict[str, Any],
    ) -> None:
        """`read_events` should call XREAD with correct streams mapping and options."""
        sample_response: List[
            Tuple[bytes, List[Tuple[bytes, Dict[bytes, bytes]]]]
        ] = [
            (
                b"test_namespace:prices",
                [
                    (b"123-0", {b"symbol": b"AAPL", b"price": b"100"}),
                ],
            ),
        ]
        redis_mocks["client"].xread.return_value = sample_response

        client = RedisStreamClient()
        result = client.read_events("prices", last_id="0-0", count=10, block_ms=None)

        assert result == sample_response
        redis_mocks["client"].xread.assert_called_once_with(
            streams={"test_namespace:prices": "0-0"},
            count=10,
            block=None,
        )


