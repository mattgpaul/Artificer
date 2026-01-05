from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep

from system.algo_trader.domain.engine import Engine
from system.algo_trader.domain.events import MarketEvent
from system.algo_trader.ports.broker import BrokerPort
from system.algo_trader.ports.data_broker import DataBrokerPort
from system.algo_trader.ports.market_data import MarketDataPort


@dataclass(slots=True)
class ForwardTestApp:
    engine: Engine
    market_data: MarketDataPort
    broker: BrokerPort
    redis_broker: DataBrokerPort
    poll_seconds: float = 2.0
    symbols: list[str] | None = None
    max_iterations: int | None = None

    def run_forever(self) -> None:
        if not self.symbols:
            raise ValueError("ForwardTestApp.symbols must be set")

        i = 0
        while True:
            for override in self.redis_broker.poll_overrides(max_items=10):
                self.engine.on_override(override)

            quotes = self.market_data.get_quotes(self.symbols)
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

            sleep(self.poll_seconds)
            i += 1
            if self.max_iterations is not None and i >= self.max_iterations:
                return

