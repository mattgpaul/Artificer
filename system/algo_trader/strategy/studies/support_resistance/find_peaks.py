"""Peak detection study using scipy.signal.find_peaks.

This module provides a study class for detecting peaks in OHLCV price data
using scipy's peak detection algorithm.
"""

from typing import Any

import pandas as pd
from scipy.signal import find_peaks

from system.algo_trader.strategy.studies.base_study import BaseStudy


class FindPeaks(BaseStudy):
    """Study for detecting peaks in price data.

    Uses scipy.signal.find_peaks to identify local maxima in price series.
    Supports various filtering parameters including height, distance, prominence,
    width, and threshold.
    """

    def __init__(self, logger=None):
        """Initialize FindPeaks study.

        Args:
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        super().__init__(logger)

    def get_field_name(self, **params: Any) -> str:
        """Get the field name for this study invocation.

        Note: FindPeaks is a multi-output study that returns a DataFrame with
        multiple columns (peak1, peak2, ...). Multi-output study support will
        be added in a future update.

        Args:
            **params: Study parameters (not currently used for field naming).

        Returns:
            String field name (placeholder for now).

        Raises:
            NotImplementedError: Multi-output studies not yet supported.
        """
        raise NotImplementedError(
            "FindPeaks is a multi-output study. Multi-output field naming "
            "support will be added in a future update."
        )

    def _validate_study_specific(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> bool:
        if len(ohlcv_data) < 3:
            self._log_validation_error(
                ticker,
                f"Insufficient data for peak detection - {len(ohlcv_data)} rows (need at least 3)",
            )
            return False
        return True

    def calculate(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> pd.DataFrame | None:
        """Calculate peaks in the price data.

        Args:
            ohlcv_data: DataFrame with OHLCV data.
            ticker: Stock ticker symbol (for logging).
            **kwargs: Additional parameters:
                column: Column name to use for peak detection (default: "close").
                height: Minimum height of peaks.
                distance: Minimum distance between peaks.
                prominence: Minimum prominence of peaks.
                width: Minimum width of peaks.
                threshold: Minimum threshold for peak detection.

        Returns:
            DataFrame with peak values in columns (peak1, peak2, ...) or None on error.
        """
        column = kwargs.get("column", "close")

        if column not in ohlcv_data.columns:
            self.logger.error(f"{ticker}: OHLCV data missing '{column}' column")
            return None

        data = ohlcv_data[column].values

        scipy_kwargs = {}
        if "height" in kwargs:
            scipy_kwargs["height"] = kwargs["height"]
        if "distance" in kwargs:
            scipy_kwargs["distance"] = kwargs["distance"]
        if "prominence" in kwargs:
            scipy_kwargs["prominence"] = kwargs["prominence"]
        if "width" in kwargs:
            scipy_kwargs["width"] = kwargs["width"]
        if "threshold" in kwargs:
            scipy_kwargs["threshold"] = kwargs["threshold"]

        try:
            peak_indices, _ = find_peaks(data, **scipy_kwargs)
        except Exception as e:
            self.logger.error(f"{ticker}: Error finding peaks: {e}")
            return None

        if len(peak_indices) == 0:
            return pd.DataFrame(index=ohlcv_data.index)

        peak_values = data[peak_indices]

        result_dict = {}
        for i, peak_value in enumerate(peak_values, start=1):
            result_dict[f"peak{i}"] = peak_value

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
        """Compute peaks with validation and error handling.

        Args:
            ohlcv_data: DataFrame with OHLCV data or None.
            ticker: Stock ticker symbol (for logging).
            column: Column name to use for peak detection (default: "close").
            height: Minimum height of peaks.
            distance: Minimum distance between peaks.
            prominence: Minimum prominence of peaks.
            width: Minimum width of peaks.
            threshold: Minimum threshold for peak detection.

        Returns:
            DataFrame with peak values or None on error/validation failure.
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
