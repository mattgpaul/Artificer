"""Override port interface for operator commands.

Defines protocol for retrieving operator override commands for runtime
configuration changes.
"""

from __future__ import annotations

from typing import Protocol

from system.algo_trader.domain.events import OverrideEvent


class OverridePort(Protocol):
    """Protocol for retrieving operator override commands."""

    def next_override(self) -> OverrideEvent | None:
        """Get next override event if available."""
        ...
