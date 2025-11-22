"""Valley detection study using scipy.signal.find_peaks.

This module provides a study class for detecting valleys (local minima) in OHLCV
price data by inverting the data and using scipy's peak detection algorithm.
"""

import pandas as pd
from scipy.signal import find_peaks

from typing import Any

from system.algo_trader.strategy.studies.base_study import BaseStudy


class FindValleys(BaseStudy):
    """Study for detecting valleys (local minima) in price data.

    Uses scipy.signal.find_peaks on inverted data to identify local minima in
    price series. Supports various filtering parameters including height,
    distance, prominence, width, and threshold.
    """

    def __init__(self, logger=None):
        """Initialize FindValleys study.

        Args:
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        super().__init__(logger)

    def get_field_name(self, **params: Any) -> str:
        """Get the field name for this study invocation.

        Note: FindValleys is a multi-output study that returns a DataFrame with
        multiple columns (valley1, valley2, ...). Multi-output study support will
        be added in a future update.

        Args:
            **params: Study parameters (not currently used for field naming).

        Returns:
            String field name (placeholder for now).

        Raises:
            NotImplementedError: Multi-output studies not yet supported.
        """
        raise NotImplementedError(
            "FindValleys is a multi-output study. Multi-output field naming "
            "support will be added in a future update."
        )

    def _validate_study_specific(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> bool:
        if len(ohlcv_data) < 3:
            self._log_validation_error(
                ticker,
                f"Insufficient data for valley detection - {len(ohlcv_data)} rows "
                f"(need at least 3)",
            )
            return False
        return True

    def _build_scipy_kwargs(self, kwargs: dict) -> dict:
        """Build scipy kwargs with proper inversion for valley detection.

        Args:
            kwargs: Dictionary of parameters from calculate method.

        Returns:
            Dictionary of scipy parameters with height inverted for valley detection.
        """
        scipy_kwargs = {}
        if "height" in kwargs:
            height = kwargs["height"]
            if isinstance(height, (int, float)):
                scipy_kwargs["height"] = -height
            elif isinstance(height, tuple) and len(height) == 2:
                scipy_kwargs["height"] = (-height[1], -height[0])
        if "distance" in kwargs:
            scipy_kwargs["distance"] = kwargs["distance"]
        if "prominence" in kwargs:
            scipy_kwargs["prominence"] = kwargs["prominence"]
        if "width" in kwargs:
            scipy_kwargs["width"] = kwargs["width"]
        if "threshold" in kwargs:
            scipy_kwargs["threshold"] = kwargs["threshold"]
        return scipy_kwargs

    def calculate(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> pd.DataFrame | None:
        """Calculate valleys in the price data.

        Args:
            ohlcv_data: DataFrame with OHLCV data.
            ticker: Stock ticker symbol (for logging).
            **kwargs: Additional parameters:
                column: Column name to use for valley detection (default: "close").
                height: Minimum height of valleys (inverted for detection).
                distance: Minimum distance between valleys.
                prominence: Minimum prominence of valleys.
                width: Minimum width of valleys.
                threshold: Minimum threshold for valley detection.

        Returns:
            DataFrame with valley values in columns (valley1, valley2, ...) or None on error.
        """
        column = kwargs.get("column", "close")

        if column not in ohlcv_data.columns:
            self.logger.error(f"{ticker}: OHLCV data missing '{column}' column")
            return None

        data = ohlcv_data[column].values
        inverted_data = -data

        scipy_kwargs = self._build_scipy_kwargs(kwargs)

        try:
            valley_indices, _ = find_peaks(inverted_data, **scipy_kwargs)
        except Exception as e:
            self.logger.error(f"{ticker}: Error finding valleys: {e}")
            return None

        if len(valley_indices) == 0:
            return pd.DataFrame(index=ohlcv_data.index)

        valley_values = data[valley_indices]

        result_dict = {}
        for i, valley_value in enumerate(valley_values, start=1):
            result_dict[f"valley{i}"] = valley_value

        result_df = pd.DataFrame(result_dict, index=ohlcv_data.index)

        return result_df

    def compute(  # noqa: PLR0913
        self,
        ohlcv_data: pd.DataFrame | None,
        ticker: str,
        column: str = "close",
        height=None,
        distance=None,
        prominence=None,
        width=None,
        threshold=None,
    ) -> pd.DataFrame | None:
        """Compute valleys with validation and error handling.

        Args:
            ohlcv_data: DataFrame with OHLCV data or None.
            ticker: Stock ticker symbol (for logging).
            column: Column name to use for valley detection (default: "close").
            height: Minimum height of valleys.
            distance: Minimum distance between valleys.
            prominence: Minimum prominence of valleys.
            width: Minimum width of valleys.
            threshold: Minimum threshold for valley detection.

        Returns:
            DataFrame with valley values or None on error/validation failure.
        """
        kwargs = {
            "required_columns": [column],
            "column": column,
        }
        if height is not None:
            kwargs["height"] = height
        if distance is not None:
            kwargs["distance"] = distance
        if prominence is not None:
            kwargs["prominence"] = prominence
        if width is not None:
            kwargs["width"] = width
        if threshold is not None:
            kwargs["threshold"] = threshold

        return super().compute(ohlcv_data=ohlcv_data, ticker=ticker, **kwargs)
