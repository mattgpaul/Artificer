"""Simple Moving Average (SMA) technical indicator study.

This module provides the SimpleMovingAverage class for calculating simple
moving averages from OHLCV data. It inherits from BaseStudy to get common
validation functionality and adds SMA-specific validation (minimum data length).
"""

import pandas as pd

from system.algo_trader.strategy.studies.base_study import BaseStudy


class SimpleMovingAverage(BaseStudy):
    """Simple Moving Average technical indicator study.

    Calculates simple moving averages using pandas rolling window. Inherits
    common validation from BaseStudy and adds validation for minimum data
    length requirement (must have at least `window` data points).

    Attributes:
        logger: Logger instance for validation and error messages.
    """

    def __init__(self, logger=None):
        """Initialize SimpleMovingAverage study.

        Args:
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        super().__init__(logger)

    def _validate_study_specific(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> bool:
        """Validate SMA-specific requirements.

        Checks that there is sufficient data for the moving average window.
        Requires at least `window` data points.

        Args:
            ohlcv_data: DataFrame with OHLCV data to validate.
            ticker: Stock ticker symbol (for logging purposes).
            **kwargs: Must contain 'window' parameter.

        Returns:
            True if sufficient data exists, False otherwise.
        """
        window = kwargs.get("window")
        if window is None:
            self._log_validation_error(ticker, "window parameter is required")
            return False

        if len(ohlcv_data) < window:
            # Only log at debug level - this is expected during early time steps in backtesting
            self._log_validation_error(
                ticker,
                f"Insufficient data for SMA calculation - {len(ohlcv_data)} rows "
                f"(need at least {window} for window={window})",
            )
            return False

        return True

    def calculate(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> pd.Series | None:
        """Calculate simple moving average.

        Uses pandas rolling window to calculate SMA. Returns a Series that
        may contain NaN values for periods with insufficient data.

        Args:
            ohlcv_data: DataFrame with OHLCV data (already validated).
            ticker: Stock ticker symbol (for logging purposes).
            **kwargs: Must contain 'window' and 'column' parameters.

        Returns:
            Series with SMA values indexed by datetime. May contain NaN for
            insufficient data periods.
        """
        window = kwargs.get("window")
        column = kwargs.get("column", "close")

        if window is None:
            self.logger.error(f"{ticker}: window parameter is required for SMA calculation")
            return None

        if column not in ohlcv_data.columns:
            self.logger.error(f"{ticker}: OHLCV data missing '{column}' column")
            return None

        # Calculate simple moving average using pandas rolling window
        sma = ohlcv_data[column].rolling(window=window).mean()

        return sma

    def compute(
        self,
        ohlcv_data: pd.DataFrame | None,
        window: int,
        ticker: str,
        column: str = "close",
    ) -> pd.Series | None:
        """Calculate simple moving average with validation.

        Public method that orchestrates validation and calculation for SMA.
        This is a convenience method that wraps the base `compute()` method
        with SMA-specific parameter handling.

        Args:
            ohlcv_data: DataFrame with OHLCV data indexed by datetime.
            window: Number of periods for the moving average.
            ticker: Stock ticker symbol (for logging purposes).
            column: Column name to calculate SMA on (default: 'close').

        Returns:
            Series with SMA values indexed by datetime, or None if validation fails.
            Series may contain NaN values for periods with insufficient data.
        """
        return super().compute(
            ohlcv_data=ohlcv_data,
            ticker=ticker,
            window=window,
            required_columns=[column],
            column=column,
        )
