"""Journal port interface for event recording.

Defines protocol for persisting decision and override events to storage.
"""

from __future__ import annotations

from typing import Protocol

from system.algo_trader.domain.events import DecisionEvent, OverrideEvent


class JournalPort(Protocol):
    """Protocol for event recording."""

    def record_decision(self, event: DecisionEvent) -> None:
        """Record decision event."""
        ...

    def record_override(self, event: OverrideEvent) -> None:
        """Record override event."""
        ...
