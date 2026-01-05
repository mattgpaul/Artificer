from __future__ import annotations

from typing import Protocol, Sequence

from system.algo_trader.domain.events import DecisionEvent, MarketEvent, OverrideEvent


class DataBrokerPort(Protocol):
    def publish_market(self, events: Sequence[MarketEvent]) -> None: ...

    def publish_decision(self, event: DecisionEvent) -> None: ...

    def publish_override(self, event: OverrideEvent) -> None: ...

    def poll_overrides(self, max_items: int = 10) -> Sequence[OverrideEvent]: ...

