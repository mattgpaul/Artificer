from typing import Any, Protocol

import pandas as pd

from infrastructure.logging.logger import get_logger


class FilterContext:
    def __init__(
        self,
        signal: dict[str, Any],
        ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None,
    ):
        self.signal = signal
        self.ohlcv_by_ticker = ohlcv_by_ticker or {}

    def get_ticker_ohlcv(self, ticker: str) -> pd.DataFrame | None:
        return self.ohlcv_by_ticker.get(ticker)


class Filter(Protocol):
    def evaluate(self, context: FilterContext) -> bool:
        pass


class FilterPipeline:
    def __init__(self, filters: list[Filter], logger=None):
        self.filters = filters
        self.logger = logger or get_logger(self.__class__.__name__)

    def is_valid(self, signal: dict[str, Any], ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None) -> bool:
        context = FilterContext(signal, ohlcv_by_ticker)
        for filter_instance in self.filters:
            try:
                if not filter_instance.evaluate(context):
                    ticker = signal.get("ticker", "unknown")
                    signal_time = signal.get("signal_time", "unknown")
                    self.logger.debug(
                        f"Filter {filter_instance.__class__.__name__} rejected signal "
                        f"for {ticker} at {signal_time}"
                    )
                    return False
            except Exception as e:
                ticker = signal.get("ticker", "unknown")
                signal_time = signal.get("signal_time", "unknown")
                self.logger.warning(
                    f"Filter {filter_instance.__class__.__name__} raised exception "
                    f"for {ticker} at {signal_time}: {e}"
                )
                return False
        return True

    def apply(self, signals: pd.DataFrame, ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
        if signals.empty:
            return signals

        if not self.filters:
            return signals

        filtered_indices = []
        for idx, signal_row in signals.iterrows():
            signal_dict = signal_row.to_dict()
            if self.is_valid(signal_dict, ohlcv_by_ticker):
                filtered_indices.append(idx)

        if not filtered_indices:
            return pd.DataFrame()

        return signals.loc[filtered_indices]

