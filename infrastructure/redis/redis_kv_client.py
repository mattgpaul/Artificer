from typing import Optional

from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisKVClient(BaseRedisClient):
    def get(self, key_id: str):
        key = self._build_key(key_id)
        try:
            raw = self.client.get(key)
            if raw is None:
                if self.metrics:
                    self.metrics.incr(
                        "redis.kv.get.miss",
                        tags={"namespace": self.namespace, "key": key_id},
                    )
                return None

            if isinstance(raw, bytes):
                value = raw.decode("utf-8")
            else:
                value = str(raw)

            self.logger.debug(f"Got value for {key}")

            if self.metrics:
                self.metrics.incr(
                    "redis.kv.get.hit",
                    tags={"namespace": self.namespace, "key": key_id},
                )

            return value
        except Exception as e:
            self.logger.error(f"Failed to retrieve {key}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.kv.get.error",
                    tags={"namespace": self.namespace, "key": key_id},
                )
            return None

    def set(self, key_id: str, value: str, ttl: Optional[int] = None) -> bool:
        key = self._build_key(key_id)
        try:
            result = self.client.set(key, value, ex=ttl)
            self.logger.debug(f"Set {key}:{value}")

            if self.metrics:
                tags = {"namespace": self.namespace, "key": key_id}
                metric_base = "redis.kv.set"
                if result:
                    self.metrics.incr(f"{metric_base}.success", tags=tags)
                else:
                    self.metrics.incr(f"{metric_base}.failure", tags=tags)

            return result > 0
        except Exception as e:
            self.logger.error(f"Failed to set {value} for {key_id}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.kv.set.error",
                    tags={"namespace": self.namespace, "key": key_id},
                )
            return False