from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisPubSubClient(BaseRedisClient):
    """Redis PubSub client for managing Redis PubSub channels.

    This client provides methods for working with Redis PubSub channels, including:
    - Creating and managing channels
    - Reading and writing messages to channels
    - Managing channel consumers
    """
    