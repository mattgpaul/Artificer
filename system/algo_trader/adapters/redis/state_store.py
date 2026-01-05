from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from infrastructure.redis.redis import BaseRedisClient


@dataclass(slots=True)
class AlgoTraderStateStore(BaseRedisClient):
    """KV latest-state store for algo_trader.

    Uses BaseRedisClient JSON helpers (namespaced keys).
    """

    def _get_namespace(self) -> str:
        return "algo_trader"

    def set_latest_quote(self, symbol: str, quote: dict[str, Any], ttl_seconds: int = 30) -> bool:
        return self.set_json(f"latest_quote:{symbol}", quote, ttl=ttl_seconds)

    def get_latest_quote(self, symbol: str) -> dict[str, Any] | None:
        val = self.get_json(f"latest_quote:{symbol}")
        return val if isinstance(val, dict) else None

    def set_engine_status(self, status: dict[str, Any], ttl_seconds: int = 10) -> bool:
        return self.set_json("engine_status", status, ttl=ttl_seconds)
