from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from system.algo_trader.domain.events import MarketEvent, OverrideEvent
from system.algo_trader.domain.models import Fill, OrderIntent


@dataclass(frozen=True, slots=True)
class PortfolioDecision:
    """Portfolio-managed decision output.

    This is produced by the PortfolioManager as a co-decision maker with the strategy.
    """

    proposed_intents: tuple[OrderIntent, ...]
    final_intents: tuple[OrderIntent, ...]
    pause_until: datetime | None = None
    audit: dict[str, Any] | None = None


class PortfolioPort(Protocol):
    def manage(self, event: MarketEvent, proposed_intents: Sequence[OrderIntent]) -> PortfolioDecision: ...

    def apply_fill(self, fill: Fill) -> None: ...

    def on_override(self, event: OverrideEvent) -> None: ...
