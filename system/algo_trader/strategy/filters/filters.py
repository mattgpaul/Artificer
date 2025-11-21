from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.filters.core import Filter, FilterContext
from system.algo_trader.strategy.studies.moving_average.simple_moving_average import (
    SimpleMovingAverage,
)


class PriceComparisonFilter:
    def __init__(self, field: str, operator: str, value: float, logger=None):
        self.field = field
        self.operator = operator
        self.value = value
        self.logger = logger or get_logger(self.__class__.__name__)
        self._validate_operator()

    def _validate_operator(self):
        valid_operators = {">", "<", ">=", "<=", "==", "!="}
        if self.operator not in valid_operators:
            raise ValueError(f"Invalid operator: {self.operator}. Must be one of {valid_operators}")

    def evaluate(self, context: FilterContext) -> bool:
        signal = context.signal
        field_value = signal.get(self.field)

        if field_value is None:
            self.logger.debug(f"Field {self.field} not found in signal, rejecting")
            return False

        try:
            field_value = float(field_value)
        except (ValueError, TypeError):
            self.logger.debug(f"Field {self.field} value {field_value} cannot be converted to float, rejecting")
            return False

        if self.operator == ">":
            return field_value > self.value
        elif self.operator == "<":
            return field_value < self.value
        elif self.operator == ">=":
            return field_value >= self.value
        elif self.operator == "<=":
            return field_value <= self.value
        elif self.operator == "==":
            return abs(field_value - self.value) < 1e-9
        elif self.operator == "!=":
            return abs(field_value - self.value) >= 1e-9
        else:
            return False


class SmaComparisonFilter:
    def __init__(
        self,
        field_fast: str,
        field_slow: str,
        operator: str,
        fast_window: int | None = None,
        slow_window: int | None = None,
        logger=None,
    ):
        self.field_fast = field_fast
        self.field_slow = field_slow
        self.operator = operator
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.logger = logger or get_logger(self.__class__.__name__)
        self.sma_study = SimpleMovingAverage()
        self._validate_operator()

    def _validate_operator(self):
        valid_operators = {">", "<", ">=", "<=", "==", "!="}
        if self.operator not in valid_operators:
            raise ValueError(f"Invalid operator: {self.operator}. Must be one of {valid_operators}")

    def _get_sma_value(self, ohlcv: pd.DataFrame, window: int, ticker: str) -> float | None:
        if ohlcv.empty or "close" not in ohlcv.columns:
            return None
        if len(ohlcv) < window:
            return None
        sma_result = self.sma_study.compute(ohlcv_data=ohlcv, window=window, ticker=ticker, column="close")
        if sma_result is None or sma_result.empty:
            return None
        return float(sma_result.iloc[-1])

    def _get_value_from_signal(self, signal: dict[str, Any], field: str) -> float | None:
        value = signal.get(field)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def evaluate(self, context: FilterContext) -> bool:
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
        else:
            if self.fast_window is None or self.slow_window is None:
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

        if self.operator == ">":
            return fast_value > slow_value
        elif self.operator == "<":
            return fast_value < slow_value
        elif self.operator == ">=":
            return fast_value >= slow_value
        elif self.operator == "<=":
            return fast_value <= slow_value
        elif self.operator == "==":
            return abs(fast_value - slow_value) < 1e-9
        elif self.operator == "!=":
            return abs(fast_value - slow_value) >= 1e-9
        else:
            return False

