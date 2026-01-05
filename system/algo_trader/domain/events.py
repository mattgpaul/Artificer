"""Domain events for algo_trader.

Defines event types used throughout the system for market data, decisions,
fills, and operator overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from system.algo_trader.domain.models import Bar, Fill, OrderIntent, Quote


@dataclass(frozen=True, slots=True)
class MarketEvent:
    """Market data event (bar or quote)."""

    kind: Literal["bar", "quote"]
    payload: Bar | Quote


@dataclass(frozen=True, slots=True)
class DecisionEvent:
    """Trading decision event with order intents."""

    ts: datetime
    order_intents: tuple[OrderIntent, ...]
    proposed_intents: tuple[OrderIntent, ...] = ()
    audit: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class FillEvent:
    """Fill event for executed trades."""

    payload: Fill


@dataclass(frozen=True, slots=True)
class OverrideEvent:
    """Operator override command event."""

    ts: datetime
    command: str
    args: dict[str, str]
