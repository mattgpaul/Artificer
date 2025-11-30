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

            if self.metrics:
                tags = {"namespace": self.namespace, "queue": queue}
                metric_base = "redis.queue.enqueue"
                if result > 0:
                    self.metrics.incr(f"{metric_base}.success", tags=tags)
                else:
                    self.metrics.incr(f"{metric_base}.noop", tags=tags)

            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to enqueue value onto {key}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.queue.enqueue.error",
                    tags={"namespace": self.namespace, "queue": queue},
                )
            return False

    def dequeue(self, queue: str, timeout: Optional[int] = None) -> bool:
        key = self._build_key(queue)
        try:
            if timeout is None:
                raw = self.client.lpop(key)
            else:
                result = self.client.blpop([key], timeout=timeout)
                if result is None:
                    if self.metrics:
                        self.metrics.incr(
                            "redis.queue.dequeue.empty",
                            tags={"namespace": self.namespace, "queue": queue},
                        )
                    return None
                _, raw = result

            if raw is None:
                if self.metrics:
                    self.metrics.incr(
                        "redis.queue.dequeue.empty",
                        tags={"namespace": self.namespace, "queue": queue},
                    )
                return None
            if isinstance(raw, bytes):
                value = raw.decode("utf-8")
            else:
                value = str(raw)

            if self.metrics:
                self.metrics.incr(
                    "redis.queue.dequeue.success",
                    tags={"namespace": self.namespace, "queue": queue},
                )

            return value
        except Exception as e:
            self.logger.error(f"Failed to dequeue from queue {key}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.queue.dequeue.error",
                    tags={"namespace": self.namespace, "queue": queue},
                )
            return None

