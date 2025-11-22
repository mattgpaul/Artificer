from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd


@dataclass
class PositionState:
    size: float = 0.0
    side: str | None = None
    entry_price: float | None = None


@dataclass
class PositionDecision:
    allow_entry: bool | None = None
    exit_fraction: float | None = None


class PositionRuleContext:
    def __init__(
        self,
        signal: dict[str, Any],
        position: PositionState,
        ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None,
    ):
        self.signal = signal
        self.position = position
        self.ohlcv_by_ticker = ohlcv_by_ticker or {}

    def get_ticker_ohlcv(self, ticker: str) -> pd.DataFrame | None:
        return self.ohlcv_by_ticker.get(ticker)


class PositionRule(Protocol):
    def evaluate(self, context: PositionRuleContext) -> PositionDecision:
        pass


def validate_exit_signal_and_get_price(
    context: PositionRuleContext, field_price: str
) -> float | None:
    """
    Validates that the position is valid for exit and extracts the current price.

    Returns the current price as a float if all validations pass, None otherwise.
    Validations:
    - Position must have size > 0 and entry_price must not be None
    - Signal must be an exit signal (matching position side with signal_type)
    - Current price must be present in signal and convertible to float
    """
    if context.position.size <= 0 or context.position.entry_price is None:
        return None

    signal_type = context.signal.get("signal_type", "")
    side = context.position.side
    is_exit = (side == "LONG" and signal_type == "sell") or (
        side == "SHORT" and signal_type == "buy"
    )
    if not is_exit:
        return None

    current = context.signal.get(field_price)
    if current is None:
        return None

    try:
        return float(current)
    except (TypeError, ValueError):
        return None

