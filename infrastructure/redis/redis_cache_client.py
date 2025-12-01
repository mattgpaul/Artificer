"""Unified Redis cache client implementation.

This module provides a Redis client for common cache operations including
string key-value get/set and JSON-encoded value get/set, all with optional
TTL support.
"""

from __future__ import annotations

import json
from typing import Any

from infrastructure.redis.base_redis_client import BaseRedisClient


class RedisCacheClient(BaseRedisClient):
    """Redis cache client for simple string and JSON operations.

    Provides methods for storing and retrieving:
    - Plain string values via ``get`` / ``set``
    - JSON-serializable values via ``get_json`` / ``set_json``

    Each operation supports optional TTL (time-to-live) and emits metrics when
    a metrics recorder is attached.
    """

    # --- string KV ---

    def get(self, key_id: str) -> str | None:
        """Retrieve a string value by key.

        Args:
            key_id: The key identifier to retrieve.

        Returns:
            The decoded string value if found, None otherwise.
        """
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

    def set(self, key_id: str, value: str, ttl: int | None = None) -> bool:
        """Set a string key-value pair with optional TTL.

        Args:
            key_id: The key identifier to set.
            value: The string value to store.
            ttl: Optional time-to-live in seconds.

        Returns:
            True if the operation succeeded, False otherwise.
        """
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

            return bool(result)
        except Exception as e:
            self.logger.error(f"Failed to set {value} for {key_id}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.kv.set.error",
                    tags={"namespace": self.namespace, "key": key_id},
                )
            return False

    # --- JSON ---

    def get_json(self, key_id: str) -> Any | None:
        """Retrieve a JSON value by key.

        Args:
            key_id: The key identifier to retrieve.

        Returns:
            The deserialized JSON value if found and valid, or None on cache
            miss or decode / parse failure.
        """
        key = self._build_key(key_id)
        try:
            raw = self.client.get(key)
            if raw is None:
                if self.metrics:
                    self.metrics.incr(
                        "redis.json.get.miss",
                        tags={"namespace": self.namespace, "key": key_id},
                    )
                return None

            if isinstance(raw, bytes):
                decoded = raw.decode("utf-8")
            else:
                decoded = str(raw)

            value = json.loads(decoded)

            self.logger.debug(f"Got JSON value for {key}")

            if self.metrics:
                self.metrics.incr(
                    "redis.json.get.hit",
                    tags={"namespace": self.namespace, "key": key_id},
                )

            return value
        except Exception as e:
            self.logger.error(f"Failed to retrieve JSON for {key}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.json.get.error",
                    tags={"namespace": self.namespace, "key": key_id},
                )
            return None

    def set_json(self, key_id: str, value: Any, ttl: int | None = None) -> bool:
        """Set a JSON-encoded value with optional TTL.

        Args:
            key_id: The key identifier to set.
            value: Any JSON-serializable value to store.
            ttl: Optional time-to-live in seconds.

        Returns:
            True if the operation succeeded, False otherwise.
        """
        key = self._build_key(key_id)
        try:
            payload = json.dumps(value)
            result = self.client.set(key, payload, ex=ttl)
            self.logger.debug(f"Set JSON for {key}")

            if self.metrics:
                tags = {"namespace": self.namespace, "key": key_id}
                metric_base = "redis.json.set"
                if result:
                    self.metrics.incr(f"{metric_base}.success", tags=tags)
                else:
                    self.metrics.incr(f"{metric_base}.failure", tags=tags)

            return bool(result)
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Failed to set JSON for {key_id}: {e}")
            if self.metrics:
                self.metrics.incr(
                    "redis.json.set.error",
                    tags={"namespace": self.namespace, "key": key_id},
                )
            return False
