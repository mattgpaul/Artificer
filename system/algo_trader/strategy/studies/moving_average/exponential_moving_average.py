from typing import Any

import pandas as pd

from system.algo_trader.strategy.studies.base_study import BaseStudy

class ExponentialMovingAverage(BaseStudy):
    def __init__(self, logger=None):
        super().__init__(logger)

    def get_field_name(self, **params: Any) -> str:
        window = params.get("window")
        if window is None:
            raise ValueError("window parameter is required for EMA field name")
        return f"ema_{window}"

    def _validate_study_specific(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs: Any) -> bool:
        window = kwargs.get("window")
        if window is None:
            self._log_validation_error(ticker, "window parameter is required")
            return False
        if len(ohlcv_data) < window:
            self._log_validation_error(ticker, "Insufficient data for EMA calculation")
            return False
        return True

    def calculate(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs: Any) -> pd.Series | None:
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
        return super().compute(
            ohlcv_data=ohlcv_data,
            ticker=ticker,
            window=window,
            required_columns=[column],
            column=column,
        )