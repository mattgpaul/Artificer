"""Unit tests / contract tests for the RedisStreamClient.

These tests define the expected behavior of a dedicated streams client built
on top of `BaseRedisClient`. They are currently marked xfail until the
implementation is provided.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest


@pytest.mark.unit
class TestRedisStreamClient:
    """Contract tests for a dedicated streams Redis client."""

    def test_add_event_uses_xadd_with_namespaced_stream(
        self,
        redis_mocks: Dict[str, Any],
        redis_stream_client,
    ) -> None:
        """`add_event` should append to a namespaced stream and return the entry ID."""
        redis_mocks["client"].xadd.return_value = "123-0"

        event_id = redis_stream_client.add_event(
            "prices",
            {"symbol": "AAPL", "price": "100"},
        )

        assert event_id == "123-0"
        redis_mocks["client"].xadd.assert_called_once_with(
            "test_namespace:prices",
            {"symbol": "AAPL", "price": "100"},
            id="*",
        )

    def test_add_event_returns_none_on_exception(
        self,
        redis_mocks: Dict[str, Any],
        redis_stream_client,
    ) -> None:
        """`add_event` should log and return None when xadd fails."""
        redis_mocks["client"].xadd.side_effect = Exception("Redis error")

        event_id = redis_stream_client.add_event("prices", {"symbol": "AAPL"})

        assert event_id is None
        redis_mocks["logger"].error.assert_called()

    def test_read_events_uses_xread_with_namespaced_stream_and_last_id(
        self,
        redis_mocks: Dict[str, Any],
        redis_stream_client,
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

        result = redis_stream_client.read_events(
            "prices",
            last_id="0-0",
            count=10,
            block_ms=None,
        )

        assert result == sample_response
        redis_mocks["client"].xread.assert_called_once_with(
            streams={"test_namespace:prices": "0-0"},
            count=10,
            block=None,
        )

    def test_read_events_emits_metrics_with_batch_size(
        self,
        redis_mocks: Dict[str, Any],
        redis_stream_client,
        redis_metrics,
    ) -> None:
        """`read_events` should emit a batch size metric when metrics are enabled."""
        sample_response: List[
            Tuple[bytes, List[Tuple[bytes, Dict[bytes, bytes]]]]
        ] = [
            (
                b"test_namespace:prices",
                [
                    (b"123-0", {b"symbol": b"AAPL", b"price": b"100"}),
                    (b"124-0", {b"symbol": b"AAPL", b"price": b"101"}),
                ],
            ),
        ]
        redis_mocks["client"].xread.return_value = sample_response
        redis_stream_client.metrics = redis_metrics  # type: ignore[attr-defined]

        result = redis_stream_client.read_events(
            "prices",
            last_id="0-0",
            count=10,
            block_ms=None,
        )

        assert result == sample_response
        redis_metrics.observe.assert_any_call(
            "redis.stream.read_events.batch_size",
            float(2),
            tags={"namespace": "test_namespace", "stream": "prices"},
        )


