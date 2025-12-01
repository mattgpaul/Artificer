"""Unit tests / contract tests for the RedisPubSubClient.

These tests define the expected behavior of a dedicated pub/sub client built
on top of `BaseRedisClient`. They are currently marked xfail until the
implementation is provided.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestRedisPubSubClient:
    """Contract tests for a dedicated pub/sub Redis client."""

    def test_publish_sends_message_to_namespaced_channel(
        self,
        redis_mocks: dict[str, Any],
        redis_pub_sub_client,
    ) -> None:
        """`publish` should namespace channels and return True on success."""
        redis_mocks["client"].publish.return_value = 1

        result = redis_pub_sub_client.publish("orders", "payload")

        assert result is True
        redis_mocks["client"].publish.assert_called_once_with(
            "test_namespace:orders",
            "payload",
        )

    def test_publish_logs_and_returns_false_on_exception(
        self,
        redis_mocks: dict[str, Any],
        redis_pub_sub_client,
    ) -> None:
        """`publish` should swallow errors, log, and return False."""
        redis_mocks["client"].publish.side_effect = Exception("Redis error")

        result = redis_pub_sub_client.publish("orders", "payload")

        assert result is False
        redis_mocks["logger"].error.assert_called()

    def test_subscribe_creates_pubsub_and_subscribes_to_namespaced_channels(
        self,
        redis_mocks: dict[str, Any],
        redis_pub_sub_client,
    ) -> None:
        """`subscribe` should create a pubsub object and subscribe to namespaced channels."""
        pubsub_mock = MagicMock()
        redis_mocks["client"].pubsub.return_value = pubsub_mock

        result = redis_pub_sub_client.subscribe(["orders", "trades"])

        redis_mocks["client"].pubsub.assert_called_once_with()
        pubsub_mock.subscribe.assert_called_once_with(
            "test_namespace:orders",
            "test_namespace:trades",
        )
        assert result is pubsub_mock

    def test_publish_emits_metrics_on_success(
        self,
        redis_mocks: dict[str, Any],
        redis_pub_sub_client,
        redis_metrics,
    ) -> None:
        """`publish` should emit a success metric when messages are delivered."""
        redis_mocks["client"].publish.return_value = 1
        redis_pub_sub_client.metrics = redis_metrics  # type: ignore[attr-defined]

        result = redis_pub_sub_client.publish("orders", "payload")

        assert result is True
        redis_metrics.incr.assert_any_call(
            "redis.pubsub.publish.success",
            tags={"namespace": "test_namespace", "channel": "orders"},
        )
