"""Market data port interface.

Defines protocol for retrieving historical bars and real-time quotes from
market data providers.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from system.algo_trader.domain.models import Bar, Quote


class MarketDataPort(Protocol):
    """Protocol for market data access."""

    def get_daily_bars(self, symbols: Sequence[str], start: date, end: date) -> Sequence[Bar]:
        """Get daily bars for symbols within date range."""
        ...

    def get_quotes(self, symbols: Sequence[str]) -> dict[str, Quote]:
        """Get current quotes for symbols."""
        ...
