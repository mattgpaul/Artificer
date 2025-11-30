from typing import Optional

from infrastructure.redis.base_redis_client import BaseRedisClient

class RedisKVClient(BaseRedisClient):

    def get(self, key_id: str):
        key = self._build_key(key_id)
        try:
            raw = self.client.get(key)
            if raw is None:
                return None

            if isinstance(raw, bytes):
                value = raw.decode("utf-8")
            else:
                value = str(raw)
            self.logger.debug(f"Got value for {key}")
            return value
        except Exception as e:
            self.logger.error(f"Failed to retrieve {key}: {e}")
            return None

    def set(self, key_id: str, value: str, ttl: Optional[int] = None) -> bool:
        try:
            key = self._build_key(key_id)
            result = self.client.set(key, value, ex=ttl)
            self.logger.debug(f"Set {key}:{value}")
            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to set {value} for {key_id}: {e}")
            return False