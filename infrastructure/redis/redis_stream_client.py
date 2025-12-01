from typing import Any

from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisStreamClient(BaseRedisClient):
    """Redis Stream client for managing Redis Streams.

    This client provides methods for working with Redis Streams, including:
    - Creating and managing streams
    - Reading and writing messages to streams
    - Managing stream consumers
    """

    def add_event(self, stream: str, fields: dict[str, Any]) -> bool:
        key = self._build_key(stream)
        try:
            event_id: str = self.client.xadd(key, fields, id="*")
            self.logger.debug(f"Added event to stream {key} with id {event_id}")

            if self.metrics:
                self.metrics.incr(
                    "redis.stream.add_event.success",
                    tags={"namespace": self.namespace, "stream": stream},
                )

            return event_id
        except Exception as e:
            self.logger.error(f"Failed to add event to stream {key}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.stream.add_event.error",
                    tags={"namespace": self.namespace, "stream": stream},
                )
            return None

    def read_events(
        self, stream: str, last_id: str, count: int, block_ms: int | None = None
    ) -> list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]]:
        key = self._build_key(stream)
        result = self.client.xread(
            streams={key: last_id},
            count=count,
            block=block_ms,
        )
        self.logger.debug(
            f"Read events from stream {key} starting at {last_id} (count={count}, block={block_ms})"
        )

        if self.metrics:
            batch_size = 0
            for _, entries in result:
                batch_size += len(entries)

            tags = {"namespace": self.namespace, "stream": stream}
            self.metrics.incr(
                "redis.stream.read_events.calls",
                tags=tags,
            )
            self.metrics.observe(
                "redis.stream.read_events.batch_size",
                float(batch_size),
                tags=tags,
            )

        return result
