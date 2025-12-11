"""Core domain models for the trading engine."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Order:
    """Represents a trading order."""

    symbol: str
    quantity: float
    order_type: str
    order_id: str | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class Position:
    """Represents a trading position."""

    symbol: str
    quantity: float
    avg_price: float
    timestamp: datetime | None = None


@dataclass
class Signal:
    """Represents a trading signal."""

    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    strength: float | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class PortfolioState:
    """Represents portfolio state at a point in time."""

    cash: float
    positions: dict[str, Position]
    total_value: float
    timestamp: datetime
