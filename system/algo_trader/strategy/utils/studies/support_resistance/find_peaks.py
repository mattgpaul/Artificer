import pandas as pd
from scipy.signal import find_peaks

from system.algo_trader.strategy.utils.studies.base_study import BaseStudy


class FindPeaks(BaseStudy):
    def __init__(self, logger=None):
        super().__init__(logger)

    def _validate_study_specific(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> bool:
        if len(ohlcv_data) < 3:
            self._log_validation_error(
                ticker,
                f"Insufficient data for peak detection - {len(ohlcv_data)} rows (need at least 3)",
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

