"""Portfolio port interface for position and risk management.

Defines protocol for managing positions, applying risk controls, and handling
fills and overrides.
"""

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
    """Protocol for portfolio and risk management."""

    def manage(
        self, event: MarketEvent, proposed_intents: Sequence[OrderIntent]
    ) -> PortfolioDecision:
        """Manage portfolio and apply risk controls to proposed intents."""
        ...

    def apply_fill(self, fill: Fill) -> None:
        """Apply fill to portfolio."""
        ...

    def on_override(self, event: OverrideEvent) -> None:
        """Process override event."""
        ...
