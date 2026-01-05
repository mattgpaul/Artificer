from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from system.algo_trader.domain.events import MarketEvent
from system.algo_trader.domain.models import OrderIntent


class StrategyPort(Protocol):
    def on_market(
        self, event: MarketEvent, portfolio: PortfolioPort
    ) -> Sequence[OrderIntent]: ...


class PortfolioPort(Protocol):
    # Forward reference for strategy typing without import cycles.
    ...
