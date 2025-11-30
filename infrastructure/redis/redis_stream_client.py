from typing import Dict, Any, List, Tuple, Optional

from infrastructure.redis.base_redis_client import BaseRedisClient

class RedisStreamClient(BaseRedisClient):
    """Redis Stream client for managing Redis Streams.

    This client provides methods for working with Redis Streams, including:
    - Creating and managing streams
    - Reading and writing messages to streams
    - Managing stream consumers
    """

    def add_event(self, stream: str, fields: Dict[str, Any]) -> bool:
        key = self._build_key(stream)
        try:
            event_id: str = self.client.xadd(key, fields, id='*')
            self.logger.debug(f"Added event to stream {key} with id {event_id}")
            return event_id
        except Exception as e:
            self.logger.error(f"Failed to add event to stream {key}: {e}")
            return None

    def read_events(
        self,
        stream: str,
        last_id: str,
        count: int,
        block_ms: Optional[int] = None
    ) -> List[Tuple[bytes, List[Tuple[bytes, Dict[bytes, bytes]]]]]:
        key = self._build_key(stream)
        result = self.client.xread(
            streams={key: last_id},
            count=count,
            block=block_ms,
        )
        self.logger.debug(
            f"Read events from stream {key} starting at {last_id} (count={count}, block={block_ms})"
        )
        return result