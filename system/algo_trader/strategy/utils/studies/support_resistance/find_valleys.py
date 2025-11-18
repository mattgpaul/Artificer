import pandas as pd
from scipy.signal import find_peaks

from system.algo_trader.strategy.utils.studies.base_study import BaseStudy


class FindValleys(BaseStudy):
    def __init__(self, logger=None):
        super().__init__(logger)

    def _validate_study_specific(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> bool:
        if len(ohlcv_data) < 3:
            self._log_validation_error(
                ticker,
                f"Insufficient data for valley detection - {len(ohlcv_data)} rows (need at least 3)",
            )
            return False
        return True

    def calculate(
        self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs
    ) -> pd.DataFrame | None:
        column = kwargs.get("column", "close")

        if column not in ohlcv_data.columns:
            self.logger.error(f"{ticker}: OHLCV data missing '{column}' column")
            return None

        data = ohlcv_data[column].values
        inverted_data = -data

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
            prominence = kwargs["prominence"]
            if isinstance(prominence, (int, float)):
                scipy_kwargs["prominence"] = prominence
            elif isinstance(prominence, tuple) and len(prominence) == 2:
                scipy_kwargs["prominence"] = prominence
        if "width" in kwargs:
            scipy_kwargs["width"] = kwargs["width"]
        if "threshold" in kwargs:
            threshold = kwargs["threshold"]
            if isinstance(threshold, (int, float)):
                scipy_kwargs["threshold"] = threshold
            elif isinstance(threshold, tuple) and len(threshold) == 2:
                scipy_kwargs["threshold"] = threshold

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

        result_df = pd.DataFrame(
            result_dict, index=ohlcv_data.index
        )

        return result_df

    def compute(
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

