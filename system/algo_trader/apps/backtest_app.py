"""Backtest application for algo_trader.

Runs historical backtests by feeding bars to the engine in chronological order
and executing trades immediately at bar close.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone

from system.algo_trader.domain.engine import Engine
from system.algo_trader.domain.events import MarketEvent
from system.algo_trader.domain.models import Bar
from system.algo_trader.ports.broker import BrokerPort


@dataclass(slots=True)
class BacktestApp:
    """Backtest application for running historical simulations."""

    engine: Engine
    broker: BrokerPort
    bars: list[Bar]

    def run(self) -> None:
        """Run the backtest by processing bars in chronological order."""
        # Feed bars in chronological order; execute immediately at bar close.
        for bar in sorted(self.bars, key=lambda b: (b.day, b.symbol)):
            ts = datetime.combine(bar.day, time(16, 0), tzinfo=timezone.utc)
            if hasattr(self.broker, "set_price"):
                self.broker.set_price(bar.symbol, bar.close, ts)  # type: ignore[attr-defined]

            decision = self.engine.on_market(MarketEvent(kind="bar", payload=bar))
            if decision and decision.order_intents:
                _ = self.broker.place_orders(decision.order_intents)
                fills = list(self.broker.poll_fills())
                if fills:
                    self.engine.on_fills(fills, ts=ts)
