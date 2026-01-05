"""Forward-test app loop (continuous quotes -> decisions -> fills)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep
from typing import Protocol

from system.algo_trader.domain.engine import Engine
from system.algo_trader.domain.events import MarketEvent
from system.algo_trader.ports.broker import BrokerPort
from system.algo_trader.ports.data_broker import DataBrokerPort
from system.algo_trader.ports.market_data import MarketDataPort


class RuntimeConfigPort(Protocol):
    """Runtime config (watchlist + polling) fetched each cycle."""

    def get_watchlist(self, engine_id: str, limit: int = 200) -> list[str]: ...

    def get_poll_seconds(self, engine_id: str, default: float = 2.0) -> float: ...


class EngineRegistryPort(Protocol):
    """Engine registry heartbeats for discovery/status."""

    def heartbeat(self, engine_id: str, status: dict, ttl_seconds: int = 15) -> None: ...


@dataclass(slots=True)
class ForwardTestApp:
    engine: Engine
    market_data: MarketDataPort
    broker: BrokerPort
    redis_broker: DataBrokerPort
    runtime_config: RuntimeConfigPort
    engine_id: str
    engine_registry: EngineRegistryPort | None = None
    status_ttl_seconds: int = 15
    max_iterations: int | None = None

    def run_forever(self) -> None:
        i = 0
        while True:
            poll_seconds = self.runtime_config.get_poll_seconds(self.engine_id, default=2.0)
            symbols = self.runtime_config.get_watchlist(self.engine_id, limit=200)

            if self.engine_registry is not None:
                self.engine_registry.heartbeat(
                    engine_id=self.engine_id,
                    status={
                            "paused": self.engine.is_paused(),
                        "watchlist_size": len(symbols),
                        "poll_seconds": poll_seconds,
                    },
                    ttl_seconds=self.status_ttl_seconds,
                )

            for override in self.redis_broker.poll_overrides(max_items=10):
                self.engine.on_override(override)

            if not symbols:
                sleep(poll_seconds)
                i += 1
                if self.max_iterations is not None and i >= self.max_iterations:
                    return
                continue

            quotes = self.market_data.get_quotes(symbols)
            now = datetime.now(tz=timezone.utc)
            for sym, quote in quotes.items():
                if hasattr(self.broker, "set_price"):
                    self.broker.set_price(sym, quote.price, now)  # type: ignore[attr-defined]
                decision = self.engine.on_market(MarketEvent(kind="quote", payload=quote))
                if decision and decision.order_intents:
                    _ = self.broker.place_orders(decision.order_intents)
                    fills = list(self.broker.poll_fills())
                    if fills:
                        self.engine.on_fills(fills, ts=now)

            sleep(poll_seconds)
            i += 1
            if self.max_iterations is not None and i >= self.max_iterations:
                return
