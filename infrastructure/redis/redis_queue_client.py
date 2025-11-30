from typing import Optional

from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisQueueClient(BaseRedisClient):
    """Redis Queue client for managing Redis Queues.

    This client provides methods for working with Redis Queues, including:
    - Creating and managing queues
    - Reading and writing messages to queues
    - Managing queue consumers
    """

    def enqueue(self, queue: str, value: str, ttl: Optional[int] = None) -> bool:
        key = self._build_key(queue)
        try:
            result = self.client.rpush(key, value)
            
            if ttl is not None:
                self.client.expire(key, ttl)
            
            self.logger.debug(f"Enqueued value onto queue {key}")
            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to enqueue value onto {key}: {e}")
            return False

    def dequeue(self, queue: str, timeout: Optional[int] = None) -> bool:
        key = self._build_key(queue)
        try:
            if timeout is None:
                raw = self.client.lpop(key)
            else:
                result = self.client.blpop([key], timeout=timeout)
                if result is None:
                    return None
                _, raw = result

            if raw is None:
                return None
            if isinstance(raw, bytes):
                return raw.decode("utf-8")
            return str(raw)
        except Exception as e:
            self.logger.error(f"Failed to dequeue from queue {key}: {e}")
            return None

