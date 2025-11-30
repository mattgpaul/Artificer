"""Unit tests / contract tests for the RedisPubSubClient.

These tests define the expected behavior of a dedicated pub/sub client built
on top of `BaseRedisClient`. They are currently marked xfail until the
implementation is provided.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from infrastructure.redis.redis_pub_sub_client import RedisPubSubClient


@pytest.mark.unit
class TestRedisPubSubClient:
    """Contract tests for a dedicated pub/sub Redis client."""

    @pytest.mark.xfail(
        reason="RedisPubSubClient.publish has not been fully implemented yet.",
        strict=False,
    )
    def test_publish_sends_message_to_namespaced_channel(
        self,
        redis_mocks: Dict[str, Any],
    ) -> None:
        """`publish` should namespace channels and return True on success."""
        redis_mocks["client"].publish.return_value = 1
        client = RedisPubSubClient()

        result = client.publish("orders", "payload")

        assert result is True
        redis_mocks["client"].publish.assert_called_once_with(
            "test_namespace:orders",
            "payload",
        )

    @pytest.mark.xfail(
        reason="RedisPubSubClient.publish error handling has not been implemented yet.",
        strict=False,
    )
    def test_publish_logs_and_returns_false_on_exception(
        self,
        redis_mocks: Dict[str, Any],
    ) -> None:
        """`publish` should swallow errors, log, and return False."""
        redis_mocks["client"].publish.side_effect = Exception("Redis error")
        client = RedisPubSubClient()

        result = client.publish("orders", "payload")

        assert result is False
        redis_mocks["logger"].error.assert_called()

    @pytest.mark.xfail(
        reason="RedisPubSubClient.subscribe has not been fully implemented yet.",
        strict=False,
    )
    def test_subscribe_creates_pubsub_and_subscribes_to_namespaced_channels(
        self,
        redis_mocks: Dict[str, Any],
    ) -> None:
        """`subscribe` should create a pubsub object and subscribe to namespaced channels."""
        from unittest.mock import MagicMock

        pubsub_mock = MagicMock()
        redis_mocks["client"].pubsub.return_value = pubsub_mock

        client = RedisPubSubClient()
        result = client.subscribe(["orders", "trades"])

        redis_mocks["client"].pubsub.assert_called_once_with()
        pubsub_mock.subscribe.assert_called_once_with(
            "test_namespace:orders",
            "test_namespace:trades",
        )
        assert result is pubsub_mock


