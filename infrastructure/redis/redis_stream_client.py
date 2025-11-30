from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisStreamClient(BaseRedisClient):
    """Redis Stream client for managing Redis Streams.

    This client provides methods for working with Redis Streams, including:
    - Creating and managing streams
    - Reading and writing messages to streams
    - Managing stream consumers
    """
