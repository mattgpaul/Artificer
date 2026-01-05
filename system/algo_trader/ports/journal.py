from __future__ import annotations

from typing import Protocol

from system.algo_trader.domain.events import DecisionEvent, OverrideEvent


class JournalPort(Protocol):
    def record_decision(self, event: DecisionEvent) -> None: ...

    def record_override(self, event: OverrideEvent) -> None: ...
