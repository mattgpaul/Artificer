"""Redis-backed runtime configuration for algo_trader engines.

Per-engine key model:
- `algo_trader:{engine_id}:watchlist` (Redis set)
- `algo_trader:{engine_id}:poll_seconds` (string/float)
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from infrastructure.redis.redis import BaseRedisClient


@dataclass(slots=True)
class AlgoTraderRuntimeConfigStore(BaseRedisClient):
    """KV/set runtime config used by long-running engines and operator tools."""

    def _get_namespace(self) -> str:
        return "algo_trader"

    def get_watchlist(self, engine_id: str, limit: int = 200) -> list[str]:
        """Return the current watchlist (bounded, sorted)."""
        items = {
            x.strip().upper() for x in self.smembers(f"{engine_id}:watchlist") if str(x).strip()
        }
        out = sorted(items)
        return out[:limit]

    def set_watchlist(
        self, engine_id: str, symbols: Iterable[str], ttl_seconds: int | None = None
    ) -> None:
        """Replace the watchlist with the given symbols."""
        key = f"{engine_id}:watchlist"
        _ = self.delete(key)
        normalized = [s.strip().upper() for s in symbols if s and s.strip()]
        if normalized:
            _ = self.sadd(key, *normalized, ttl=ttl_seconds)

    def add_to_watchlist(
        self, engine_id: str, symbols: Iterable[str], ttl_seconds: int | None = None
    ) -> None:
        """Add symbols to the watchlist (placeholder for engine-driven updates)."""
        normalized = [s.strip().upper() for s in symbols if s and s.strip()]
        if normalized:
            _ = self.sadd(f"{engine_id}:watchlist", *normalized, ttl=ttl_seconds)

    def remove_from_watchlist(self, engine_id: str, symbols: Iterable[str]) -> None:
        """Remove symbols from the watchlist (placeholder for engine-driven updates)."""
        normalized = [s.strip().upper() for s in symbols if s and s.strip()]
        if normalized:
            _ = self.srem(f"{engine_id}:watchlist", *normalized)

    def get_poll_seconds(self, engine_id: str, default: float = 2.0) -> float:
        """Return polling rate in seconds (float)."""
        raw = self.get(f"{engine_id}:poll_seconds")
        if raw is None:
            return default
        try:
            v = float(raw)
        except Exception:
            return default
        return v if v > 0 else default

    def set_poll_seconds(
        self, engine_id: str, poll_seconds: float, ttl_seconds: int | None = None
    ) -> None:
        """Set polling rate (seconds) as a string/float."""
        v = float(poll_seconds)
        if v <= 0:
            raise ValueError("poll_seconds must be > 0")
        _ = self.set(f"{engine_id}:poll_seconds", str(v), ttl=ttl_seconds)
