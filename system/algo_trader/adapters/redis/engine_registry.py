"""Redis engine registry for algo_trader.

This supports discovery for 2–10 concurrent engines sharing a single Redis instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from infrastructure.redis.redis import BaseRedisClient


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(slots=True)
class AlgoTraderEngineRegistry(BaseRedisClient):
    """Registers active engine IDs and publishes a TTL'd status blob."""

    def _get_namespace(self) -> str:
        return "algo_trader"

    def register(self, engine_id: str, status: dict[str, Any] | None = None, ttl_seconds: int = 15) -> None:
        """Register `engine_id` as active and write a status heartbeat."""
        _ = self.sadd("engines", engine_id)
        self.heartbeat(engine_id=engine_id, status=status or {}, ttl_seconds=ttl_seconds)

    def heartbeat(self, engine_id: str, status: dict[str, Any], ttl_seconds: int = 15) -> None:
        """Update engine status with TTL (heartbeat)."""
        payload = dict(status)
        payload.setdefault("engine_id", engine_id)
        payload["ts"] = _utc_now().isoformat()
        _ = self.set_json(f"{engine_id}:status", payload, ttl=ttl_seconds)

    def list_engines(self) -> list[str]:
        """Return the registered engine IDs (may include stale IDs)."""
        return sorted({str(x) for x in self.smembers("engines")})

    def get_status(self, engine_id: str) -> dict[str, Any] | None:
        """Return the last heartbeat status for an engine, if present."""
        val = self.get_json(f"{engine_id}:status")
        return val if isinstance(val, dict) else None

