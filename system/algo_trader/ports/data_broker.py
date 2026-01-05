"""Data broker port interface for event publishing and consumption.

Defines protocol for publishing market events, decisions, and overrides, as
well as polling for override events.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from system.algo_trader.domain.events import DecisionEvent, MarketEvent, OverrideEvent


class DataBrokerPort(Protocol):
    """Protocol for event publishing and consumption."""

    def publish_market(self, events: Sequence[MarketEvent]) -> None:
        """Publish market events."""
        ...

    def publish_decision(self, event: DecisionEvent) -> None:
        """Publish decision event."""
        ...

    def publish_override(self, event: OverrideEvent) -> None:
        """Publish override event."""
        ...

    def poll_overrides(self, max_items: int = 10) -> Sequence[OverrideEvent]:
        """Poll for override events."""
        ...
