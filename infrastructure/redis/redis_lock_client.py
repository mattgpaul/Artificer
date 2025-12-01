"""Redis distributed lock client implementation.

This module provides a Redis client for distributed locking operations,
enabling coordination across threads and processes.
"""

from uuid import uuid4

from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisLockClient(BaseRedisClient):
    """Redis-based distributed lock client.

    This client provides simple, non-reentrant locks suitable for coordinating
    work across threads and processes.
    """

    # Lua script for safe unlock: only delete the key if the stored token
    # matches the caller's token.
    _UNLOCK_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    def acquire_lock(self, name: str, ttl: int = 30) -> str | None:
        """Attempt to acquire a lock on ``name``.

        Returns a lock token (string) if acquired, or None if the lock is
        already held or an error occurs.
        """
        key = self._build_key(f"lock:{name}")
        token = str(uuid4())

        try:
            # SET key token NX EX ttl -> acquire lock only if it does not exist.
            acquired = self.client.set(key, token, ex=ttl, nx=True)
            if not acquired:
                if self.metrics:
                    self.metrics.incr(
                        "redis.lock.acquire.contended",
                        tags={"namespace": self.namespace, "lock": name},
                    )
                return None

            self.logger.debug("Acquired lock %s with token %s", key, token)

            if self.metrics:
                self.metrics.incr(
                    "redis.lock.acquire.success",
                    tags={"namespace": self.namespace, "lock": name},
                )

            return token
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Failed to acquire lock %s: %s", key, exc)
            if self.metrics:
                self.metrics.incr(
                    "redis.lock.acquire.error",
                    tags={"namespace": self.namespace, "lock": name},
                )
            return None

    def release_lock(self, name: str, token: str) -> bool:
        """Release the lock on ``name`` if the token matches.

        Uses a small Lua script to ensure we only delete the lock if the
        stored token matches the caller's token, avoiding "unlocking
        someone else's lock" in concurrent scenarios.
        """
        key = self._build_key(f"lock:{name}")

        try:
            result = self.client.eval(self._UNLOCK_SCRIPT, 1, key, token)
            released = bool(result)

            if released:
                self.logger.debug("Released lock %s with token %s", key, token)
                if self.metrics:
                    self.metrics.incr(
                        "redis.lock.release.success",
                        tags={"namespace": self.namespace, "lock": name},
                    )
            else:
                self.logger.warning(
                    "Did not release lock %s; token mismatch or missing key",
                    key,
                )
                if self.metrics:
                    self.metrics.incr(
                        "redis.lock.release.noop",
                        tags={"namespace": self.namespace, "lock": name},
                    )

            return released
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Failed to release lock %s: %s", key, exc)
            if self.metrics:
                self.metrics.incr(
                    "redis.lock.release.error",
                    tags={"namespace": self.namespace, "lock": name},
                )
            return False
