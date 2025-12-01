"""Redis PubSub client implementation.

This module provides a Redis client for publish-subscribe operations,
enabling message broadcasting and subscription patterns.
"""

from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisPubSubClient(BaseRedisClient):
    """Redis PubSub client for managing Redis PubSub channels.

    This client provides methods for working with Redis PubSub channels, including:
    - Creating and managing channels
    - Reading and writing messages to channels
    - Managing channel consumers
    """

    def publish(self, channel: str, message: str) -> bool:
        """Publish a message to a channel.

        Args:
            channel: The channel name to publish to.
            message: The message content to publish.

        Returns:
            True if message was published, False otherwise.
        """
        namespaced = self._build_key(channel)
        try:
            result = self.client.publish(namespaced, message)
            self.logger.debug(f"Published to {namespaced}")

            if self.metrics:
                tags = {"namespace": self.namespace, "channel": channel}
                metric_base = "redis.pubsub.publish"
                if result > 0:
                    self.metrics.incr(f"{metric_base}.success", tags=tags)
                else:
                    self.metrics.incr(f"{metric_base}.noop", tags=tags)

            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to publish to {namespaced}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.pubsub.publish.error",
                    tags={"namespace": self.namespace, "channel": channel},
                )
            return False

    def subscribe(self, channels: list[str]):
        """Subscribe to one or more channels.

        Args:
            channels: List of channel names to subscribe to.

        Returns:
            Redis pubsub object for receiving messages.
        """
        pubsub = self.client.pubsub()
        namespaced_channels: list[str] = [self._build_key(c) for c in channels]
        pubsub.subscribe(*namespaced_channels)
        self.logger.debug(f"Subscribed to channels: {channels}")

        if self.metrics:
            for channel in channels:
                self.metrics.incr(
                    "redis.pubsub.subscribe",
                    tags={"namespace": self.namespace, "channel": channel},
                )

        return pubsub
