"""SMA comparison filter implementation.

This module provides a filter that compares two Simple Moving Average (SMA) values,
either from signal fields or computed from OHLCV data.
"""

from typing import Any, ClassVar

import pandas as pd

from system.algo_trader.strategy.filters.base import BaseComparisonFilter
from system.algo_trader.strategy.filters.core import FilterContext
from system.algo_trader.strategy.studies.moving_average.simple_moving_average import (
    SimpleMovingAverage,
)


class SmaComparisonFilter(BaseComparisonFilter):
    """Filter that compares two SMA (Simple Moving Average) values."""

    filter_type: ClassVar[str] = "sma_comparison"

    def __init__(
        self,
        field_fast: str,
        field_slow: str,
        operator: str,
        windows: tuple[int | None, int | None] | None = None,
        logger=None,
    ):
        """Initialize SMA comparison filter.

        Args:
            field_fast: Name of signal field for fast SMA, or used as fallback.
            field_slow: Name of signal field for slow SMA, or used as fallback.
            operator: Comparison operator (>, <, >=, <=, ==, !=).
            windows: Optional tuple of (fast_window, slow_window) for computing SMAs from OHLCV.
            logger: Optional logger instance.
        """
        super().__init__(operator, logger)
        self.field_fast = field_fast
        self.field_slow = field_slow
        self.fast_window = windows[0] if windows else None
        self.slow_window = windows[1] if windows else None
        self.sma_study = SimpleMovingAverage()

    def _get_sma_value(self, ohlcv: pd.DataFrame, window: int, ticker: str) -> float | None:
        """Compute SMA value from OHLCV data."""
        if ohlcv.empty or "close" not in ohlcv.columns:
            return None
        if len(ohlcv) < window:
            return None
        sma_result = self.sma_study.compute(
            ohlcv_data=ohlcv, window=window, ticker=ticker, column="close"
        )
        if sma_result is None or sma_result.empty:
            return None
        return float(sma_result.iloc[-1])

    def _get_value_from_signal(self, signal: dict[str, Any], field: str) -> float | None:
        """Extract and convert a numeric value from a signal field."""
        value = signal.get(field)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def evaluate(self, context: FilterContext) -> bool:
        """Evaluate whether the SMA comparison passes.

        Args:
            context: FilterContext containing signal and OHLCV data.

        Returns:
            True if comparison succeeds, False otherwise.
        """
        signal = context.signal
        ticker = signal.get("ticker")
        if not ticker:
            self.logger.debug("Signal missing ticker, rejecting")
            return False

        ohlcv = context.get_ticker_ohlcv(ticker)
        if ohlcv is None or ohlcv.empty:
            fast_value = self._get_value_from_signal(signal, self.field_fast)
            slow_value = self._get_value_from_signal(signal, self.field_slow)
            if fast_value is None or slow_value is None:
                self.logger.debug(f"Cannot compute SMA values for {ticker}, rejecting")
                return False
        elif self.fast_window is None or self.slow_window is None:
            fast_value = self._get_value_from_signal(signal, self.field_fast)
            slow_value = self._get_value_from_signal(signal, self.field_slow)
            if fast_value is None or slow_value is None:
                self.logger.debug(f"Cannot get SMA values from signal for {ticker}, rejecting")
                return False
        else:
            fast_value = self._get_sma_value(ohlcv, self.fast_window, ticker)
            slow_value = self._get_sma_value(ohlcv, self.slow_window, ticker)
            if fast_value is None or slow_value is None:
                self.logger.debug(f"Cannot compute SMA values for {ticker}, rejecting")
                return False

        return self._compare_values(fast_value, slow_value)

    @classmethod
    def from_config(cls, params: dict[str, Any], logger=None) -> "SmaComparisonFilter" | None:
        field_fast = params.get("field_fast")
        field_slow = params.get("field_slow")
        operator = params.get("operator")
        fast_window = params.get("fast_window")
        slow_window = params.get("slow_window")

        if field_fast is None or field_slow is None or operator is None:
            if logger is not None:
                logger.error(
                    "sma_comparison filter missing required params: "
                    "field_fast, field_slow, operator"
                )
            return None

        windows: tuple[int | None, int | None] | None = None
        if fast_window is not None or slow_window is not None:
            windows = (fast_window, slow_window)

        return cls(
            field_fast=field_fast,
            field_slow=field_slow,
            operator=operator,
            windows=windows,
            logger=logger,
        )
