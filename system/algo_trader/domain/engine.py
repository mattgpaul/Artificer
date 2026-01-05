from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from system.algo_trader.domain.events import DecisionEvent, MarketEvent, OverrideEvent
from system.algo_trader.domain.models import Fill
from system.algo_trader.ports.clock import ClockPort
from system.algo_trader.ports.journal import JournalPort
from system.algo_trader.ports.portfolio import PortfolioPort
from system.algo_trader.ports.strategy import StrategyPort


@dataclass(slots=True)
class Engine:
    clock: ClockPort
    strategy: StrategyPort
    portfolio: PortfolioPort
    journal: JournalPort

    paused: bool = False

    def on_market(self, event: MarketEvent) -> DecisionEvent | None:
        if self.paused:
            return None

        intents = self.strategy.on_market(event, self.portfolio)
        intents = self.portfolio.validate(intents)

        ts = self.clock.now()
        decision = DecisionEvent(ts=ts, order_intents=tuple(intents))
        self.journal.record_decision(decision)
        return decision

    def on_override(self, event: OverrideEvent) -> None:
        self.journal.record_override(event)

        cmd = event.command.lower().strip()
        if cmd == "pause":
            self.paused = True
            return
        if cmd == "resume":
            self.paused = False
            return

        # Portfolio-scoped overrides
        self.portfolio.on_override(event)

    def on_fills(self, fills: list[Fill], ts: datetime | None = None) -> None:
        _ = ts
        for fill in fills:
            self.portfolio.apply_fill(fill)
            if hasattr(self.journal, "record_fill"):
                # Optional extension point; Timescale adapter will implement this.
                self.journal.record_fill(fill)  # type: ignore[attr-defined]

