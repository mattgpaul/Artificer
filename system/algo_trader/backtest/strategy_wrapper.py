from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from system.algo_trader.strategy.base import BaseStrategy


class BacktestStrategyWrapper:
    def __init__(
        self,
        strategy: "BaseStrategy",
        current_time: pd.Timestamp,
        data_cache: dict[str, pd.DataFrame],
    ):
        self.strategy = strategy
        self.current_time = current_time
        self._data_cache = data_cache

    def query_ohlcv(
        self,
        ticker: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame | None:
        if ticker not in self._data_cache:
            return None

        full_data = self._data_cache[ticker]

        filtered_data = full_data[full_data.index <= self.current_time].copy()

        if start_time:
            start_ts = pd.to_datetime(start_time)
            filtered_data = filtered_data[filtered_data.index >= start_ts]

        if end_time:
            end_ts = pd.to_datetime(end_time)
            filtered_data = filtered_data[filtered_data.index <= end_ts]

        if limit:
            filtered_data = filtered_data.tail(limit)

        return filtered_data if not filtered_data.empty else None

    def __getattr__(self, name: str):
        return getattr(self.strategy, name)

