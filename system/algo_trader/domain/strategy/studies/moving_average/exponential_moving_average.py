"""Exponential Moving Average (EMA) study implementation.

This module provides a study that calculates exponential moving averages over
a specified window period for OHLCV data.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from system.algo_trader.domain.strategy.studies.base_study import BaseStudy


class ExponentialMovingAverage(BaseStudy):
    """Study that calculates exponential moving averages.

    Computes EMA values using pandas' exponential weighted moving average (EWM)
    with a specified span window. The EMA gives more weight to recent data points
    compared to a simple moving average.

    Args:
        logger: Optional logger instance for logging calculations and errors.
    """

    def __init__(self, logger=None):
        """Initialize the ExponentialMovingAverage study.

        Args:
            logger: Optional logger instance.
        """
        super().__init__(logger)

    def get_field_name(self, **params: Any) -> str:
        """Generate the field name for the EMA study result.

        Args:
            **params: Study parameters, must include 'window'.

        Returns:
            Field name string in format 'ema_{window}'.

        Raises:
            ValueError: If window parameter is not provided.
        """
        window = params.get("window")
        if window is None:
            raise ValueError("window parameter is required for EMA field name")
        return f"ema_{window}"

    def _validate_study_specific(
        self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs: Any
    ) -> bool:
        window = kwargs.get("window")
        if window is None:
            self._log_validation_error(ticker, "window parameter is required")
            return False
        if len(ohlcv_data) < window:
            self._log_validation_error(ticker, "Insufficient data for EMA calculation")
            return False
        return True

    def calculate(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs: Any) -> pd.Series | None:
        """Calculate the exponential moving average for the given data.

        Args:
            ohlcv_data: DataFrame containing OHLCV data.
            ticker: Ticker symbol (used for logging).
            **kwargs: Study parameters, must include 'window' and optionally 'column'.

        Returns:
            Series containing EMA values if calculation succeeds, None otherwise.
        """
        window = kwargs.get("window")
        column = kwargs.get("column", "close")
        if window is None:
            self._log_validation_error(ticker, "window parameter is required")
            return None
        if column not in ohlcv_data.columns:
            self._log_validation_error(ticker, f"OHLCV data missing '{column}' column")
            return None
        ema = ohlcv_data[column].ewm(span=window, adjust=False).mean()
        return ema

    def compute(
        self,
        ohlcv_data: pd.DataFrame | None,
        window: int,
        ticker: str,
        column: str = "close",
    ) -> pd.Series | None:
        """Compute EMA with explicit parameter interface.

        Args:
            ohlcv_data: DataFrame containing OHLCV data, or None.
            window: EMA window period.
            ticker: Ticker symbol.
            column: Column name to calculate EMA on (default: "close").

        Returns:
            Series containing EMA values if calculation succeeds, None otherwise.
        """
        return super().compute(
            ohlcv_data=ohlcv_data,
            ticker=ticker,
            window=window,
            required_columns=[column],
            column=column,
        )
