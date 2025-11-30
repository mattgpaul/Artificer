from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisQueueClient(BaseRedisClient):
    """Redis Queue client for managing Redis Queues.

    This client provides methods for working with Redis Queues, including:
    - Creating and managing queues
    - Reading and writing messages to queues
    - Managing queue consumers
    """
