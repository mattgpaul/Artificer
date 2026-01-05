from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from system.algo_trader.domain.models import Bar, Fill, OrderIntent, Quote


@dataclass(frozen=True, slots=True)
class MarketEvent:
    kind: Literal["bar", "quote"]
    payload: Bar | Quote


@dataclass(frozen=True, slots=True)
class DecisionEvent:
    ts: datetime
    order_intents: tuple[OrderIntent, ...]


@dataclass(frozen=True, slots=True)
class FillEvent:
    payload: Fill


@dataclass(frozen=True, slots=True)
class OverrideEvent:
    ts: datetime
    command: str
    args: dict[str, str]
