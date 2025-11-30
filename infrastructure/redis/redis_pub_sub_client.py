from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisPubSubClient(BaseRedisClient):
    """Redis PubSub client for managing Redis PubSub channels.

    This client provides methods for working with Redis PubSub channels, including:
    - Creating and managing channels
    - Reading and writing messages to channels
    - Managing channel consumers
    """
    
    def publish(self, channel: str, message: str) -> bool:
        namespaced = self._build_key(channel)
        try:
            result = self.client.publish(namespaced, message)
            self.logger.debug(f"Published to {namespaced}")
            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to publish to {namespaced}: {e}")
            return False

    def subscribe(self, channels: list[str]) -> bool:
        pubsub = self.client.pubsub()
        namespaced_channels: list[str] = [self._build_key(c) for c in channels]
        pubsub.subscribe(*namespaced_channels)
        self.logger.debug(f"Subscribed to channels: {channels}")
        return pubsub
