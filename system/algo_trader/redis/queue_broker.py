import json
from typing import Any

from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis import BaseRedisClient


class QueueBroker(BaseRedisClient):
    def __init__(self, namespace: str = "queue", config=None) -> None:
        self._namespace = namespace
        super().__init__(config=config)
        self.logger = get_logger(self.__class__.__name__)

    def _get_namespace(self) -> str:
        return self._namespace

    def _build_queue_key(self, queue_name: str, suffix: str) -> str:
        return f"{queue_name}:{suffix}"

    def enqueue(
        self, queue_name: str, item_id: str, data: dict[str, Any], ttl: int = 3600
    ) -> bool:
        try:
            data_key = self._build_queue_key(queue_name, f"data:{item_id}")
            pending_key = self._build_queue_key(queue_name, "pending")

            success = self.set_json(data_key, data, ttl=ttl)
            if not success:
                self.logger.error(f"Failed to store data for {item_id}")
                return False

            list_length = self.rpush(pending_key, item_id)
            if list_length > 0:
                self.logger.debug(
                    f"Enqueued {item_id} to {queue_name} (queue size: {list_length})"
                )
                return True
            else:
                self.logger.error(f"Failed to add {item_id} to pending queue")
                self.delete(data_key)
                return False

        except Exception as e:
            self.logger.error(f"Error enqueueing {item_id}: {e}")
            return False

    def dequeue(self, queue_name: str) -> str | None:
        try:
            pending_key = self._build_queue_key(queue_name, "pending")
            item_id = self.lpop(pending_key)

            if item_id:
                self.logger.debug(f"Dequeued {item_id} from {queue_name}")
                return item_id
            return None

        except Exception as e:
            self.logger.error(f"Error dequeuing from {queue_name}: {e}")
            return None

    def get_data(self, queue_name: str, item_id: str) -> dict[str, Any] | None:
        try:
            data_key = self._build_queue_key(queue_name, f"data:{item_id}")
            data = self.get_json(data_key)

            if data:
                self.logger.debug(f"Retrieved data for {item_id}")
                return data
            else:
                self.logger.warning(f"No data found for {item_id}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting data for {item_id}: {e}")
            return None

    def delete_data(self, queue_name: str, item_id: str) -> bool:
        try:
            data_key = self._build_queue_key(queue_name, f"data:{item_id}")
            success = self.delete(data_key)

            if success:
                self.logger.debug(f"Deleted data for {item_id}")
            else:
                self.logger.warning(f"Failed to delete data for {item_id}")

            return success

        except Exception as e:
            self.logger.error(f"Error deleting data for {item_id}: {e}")
            return False

    def get_queue_size(self, queue_name: str) -> int:
        try:
            pending_key = self._build_queue_key(queue_name, "pending")
            size = self.llen(pending_key)
            self.logger.debug(f"Queue {queue_name} size: {size}")
            return size

        except Exception as e:
            self.logger.error(f"Error getting queue size for {queue_name}: {e}")
            return 0

    def peek_queue(self, queue_name: str, count: int = 10) -> list[str]:
        try:
            pending_key = self._build_queue_key(queue_name, "pending")
            items = self.lrange(pending_key, 0, count - 1)
            self.logger.debug(f"Peeked {len(items)} items from {queue_name}")
            return items

        except Exception as e:
            self.logger.error(f"Error peeking queue {queue_name}: {e}")
            return []
