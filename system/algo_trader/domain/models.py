"""Domain models for algo_trader.

Defines core data structures including orders, fills, bars, quotes, and
trading sides.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class Side(str, Enum):
    """Trading side (buy or sell)."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class Bar:
    """OHLCV bar for a symbol on a given day."""

    symbol: str
    day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True, slots=True)
class Quote:
    """Real-time quote for a symbol."""

    symbol: str
    ts: datetime
    price: Decimal
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: int | None = None


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """Intent to place an order."""

    symbol: str
    side: Side
    qty: Decimal
    reason: str
    reference_price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Fill:
    """Executed trade fill."""

    symbol: str
    side: Side
    qty: Decimal
    price: Decimal
    ts: datetime
