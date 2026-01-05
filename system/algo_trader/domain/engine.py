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
    pause_until: datetime | None = None

    def is_paused(self, ts: datetime | None = None) -> bool:
        """Return whether trading is currently paused (manual or cooldown)."""
        now = ts or self.clock.now()
        if self.paused:
            return True
        return self.pause_until is not None and now < self.pause_until

    def on_market(self, event: MarketEvent) -> DecisionEvent | None:
        ts = self.clock.now()
        effective_paused = self.is_paused(ts)

        proposed = [] if effective_paused else self.strategy.on_market(event, self.portfolio)
        managed = self.portfolio.manage(event, proposed)

        if managed.pause_until is not None:
            if self.pause_until is None or managed.pause_until > self.pause_until:
                self.pause_until = managed.pause_until

        decision = DecisionEvent(
            ts=ts,
            order_intents=managed.final_intents,
            proposed_intents=managed.proposed_intents,
            audit=managed.audit,
        )

        # If we're paused and there is nothing to do/audit, skip emitting a decision.
        if effective_paused and not decision.order_intents and not decision.proposed_intents and not decision.audit:
            return None

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
            self.pause_until = None
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
