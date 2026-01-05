from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class Bar:
    symbol: str
    day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    ts: datetime
    price: Decimal
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: int | None = None


@dataclass(frozen=True, slots=True)
class OrderIntent:
    symbol: str
    side: Side
    qty: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class Fill:
    symbol: str
    side: Side
    qty: Decimal
    price: Decimal
    ts: datetime
