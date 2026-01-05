"""Strategy port interface for trading logic.

Defines protocol for strategies to generate order intents based on market
events and portfolio state.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from system.algo_trader.domain.events import MarketEvent
from system.algo_trader.domain.models import OrderIntent


class StrategyPort(Protocol):
    """Protocol for trading strategy implementations."""

    def on_market(self, event: MarketEvent, portfolio: PortfolioPort) -> Sequence[OrderIntent]:
        """Generate order intents based on market event."""
        ...


class PortfolioPort(Protocol):
    """Forward reference for strategy typing without import cycles."""

    ...
