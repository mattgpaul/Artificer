"""Clock port interface for time access.

Provides abstraction for time sources, allowing for test clocks and real-time
clocks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    """Protocol for time access."""

    def now(self) -> datetime:
        """Get current datetime."""
        ...
