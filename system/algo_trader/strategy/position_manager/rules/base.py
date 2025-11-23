from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd


@dataclass
class PositionState:
    size: float = 0.0
    side: str | None = None
    entry_price: float | None = None
    size_shares: float = 0.0
    avg_entry_price: float = 0.0


@dataclass
class PositionDecision:
    allow_entry: bool | None = None
    exit_fraction: float | None = None
    reason: str | None = None


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


def compute_anchor_price(
    context: PositionRuleContext,
    anchor_type: str,
    anchor_field: str,
    lookback_bars: int | None = None,
) -> float | None:
    """Compute an anchor price for TP/SL-style rules based on configuration.

    Supports:
    - 'entry_price': use the position's entry_price
    - 'rolling_max': max(anchor_field) over optional lookback window up to signal_time
    - 'rolling_min': min(anchor_field) over optional lookback window up to signal_time
    """
    anchor_type = anchor_type or "entry_price"
    if anchor_type == "entry_price":
        return context.position.entry_price

    ticker = context.signal.get("ticker")
    if ticker is None:
        return None

    ohlcv = context.get_ticker_ohlcv(ticker)
    if ohlcv is None or ohlcv.empty:
        return None

    ts = context.signal.get("signal_time")
    if ts is not None:
        try:
            ohlcv_slice = ohlcv.loc[ohlcv.index <= ts]
        except Exception:
            ohlcv_slice = ohlcv
    else:
        ohlcv_slice = ohlcv

    if lookback_bars is not None and lookback_bars > 0:
        ohlcv_slice = ohlcv_slice.tail(lookback_bars)

    if anchor_field not in ohlcv_slice.columns or ohlcv_slice.empty:
        return None

    series = ohlcv_slice[anchor_field]
    if anchor_type == "rolling_max":
        return float(series.max())
    if anchor_type == "rolling_min":
        return float(series.min())

    # Fallback: entry_price
    return context.position.entry_price


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

