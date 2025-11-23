"""Base classes and utilities for position management rules.

This module defines the core data structures and protocols used by position
management rules, including PositionState, PositionDecision, PositionRuleContext,
and the PositionRule protocol.
"""

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd


@dataclass
class AnchorConfig:
    """Configuration for anchor price calculation.

    Attributes:
        anchor_type: Type of anchor price ('entry_price', 'rolling_max', 'rolling_min').
        anchor_field: Field name for rolling anchor calculations.
        lookback_bars: Number of bars to look back for rolling calculations.
        one_shot: Whether rule fires only once per position lifecycle.
    """

    anchor_type: str = "entry_price"
    anchor_field: str | None = None
    lookback_bars: int | None = None
    one_shot: bool = True


@dataclass
class PositionState:
    """Represents the current state of a trading position.

    Attributes:
        size: Position size as a fraction (0.0 to 1.0+).
        side: Position side ('LONG' or 'SHORT').
        entry_price: Initial entry price.
        size_shares: Position size in shares.
        avg_entry_price: Average entry price (for scaled positions).
    """

    size: float = 0.0
    side: str | None = None
    entry_price: float | None = None
    size_shares: float = 0.0
    avg_entry_price: float = 0.0


@dataclass
class PositionDecision:
    """Represents a decision made by a position rule.

    Attributes:
        allow_entry: Whether entry is allowed (True/False/None for no opinion).
        exit_fraction: Fraction of position to exit (0.0 to 1.0).
        reason: Optional reason string for the decision.
    """

    allow_entry: bool | None = None
    exit_fraction: float | None = None
    reason: str | None = None


class PositionRuleContext:
    """Context provided to position rules for evaluation.

    Attributes:
        signal: Current trading signal dictionary.
        position: Current position state.
        ohlcv_by_ticker: Dictionary mapping ticker to OHLCV DataFrames.
    """

    def __init__(
        self,
        signal: dict[str, Any],
        position: PositionState,
        ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None,
    ):
        """Initialize rule context.

        Args:
            signal: Current trading signal dictionary.
            position: Current position state.
            ohlcv_by_ticker: Optional dictionary mapping ticker to OHLCV DataFrames.
        """
        self.signal = signal
        self.position = position
        self.ohlcv_by_ticker = ohlcv_by_ticker or {}

    def get_ticker_ohlcv(self, ticker: str) -> pd.DataFrame | None:
        """Get OHLCV data for a specific ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            OHLCV DataFrame if available, None otherwise.
        """
        return self.ohlcv_by_ticker.get(ticker)


class PositionRule(Protocol):
    """Protocol for position management rules.

    All position rules must implement the evaluate method which takes a
    PositionRuleContext and returns a PositionDecision.
    """

    def evaluate(self, context: PositionRuleContext) -> PositionDecision:
        """Evaluate the rule and return a decision.

        Args:
            context: Rule evaluation context.

        Returns:
            PositionDecision indicating the rule's decision.
        """
        pass


def _get_ohlcv_slice(
    context: PositionRuleContext,
    ticker: str,
    anchor_field: str,
    lookback_bars: int | None = None,
) -> pd.Series | None:
    """Get OHLCV data slice for anchor price calculation.

    Args:
        context: Position rule context.
        ticker: Ticker symbol.
        anchor_field: Field name for anchor calculation.
        lookback_bars: Optional number of bars to look back.

    Returns:
        Series of anchor_field values if available, None otherwise.
    """
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

    return ohlcv_slice[anchor_field]


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

    series = _get_ohlcv_slice(context, ticker, anchor_field, lookback_bars)
    if series is None:
        return None

    if anchor_type == "rolling_max":
        return float(series.max())
    if anchor_type == "rolling_min":
        return float(series.min())

    # Fallback: entry_price
    return context.position.entry_price


def validate_exit_signal_and_get_price(
    context: PositionRuleContext, field_price: str
) -> float | None:
    """Validates that the position is valid for exit and extracts the current price.

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
