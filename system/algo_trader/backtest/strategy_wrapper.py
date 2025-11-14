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

        # Ensure current_time is timezone-aware (UTC) for comparison
        current_time_utc = self.current_time
        if current_time_utc.tz is None:
            current_time_utc = current_time_utc.tz_localize("UTC")
        else:
            current_time_utc = current_time_utc.tz_convert("UTC")

        # Work with a copy to avoid modifying cached data
        # Ensure index is timezone-aware (UTC) for comparison
        filtered_data = full_data.copy()
        if filtered_data.index.tz is None:
            filtered_data.index = filtered_data.index.tz_localize("UTC")
        else:
            filtered_data.index = filtered_data.index.tz_convert("UTC")

        filtered_data = filtered_data[filtered_data.index <= current_time_utc]

        if start_time:
            start_ts = pd.to_datetime(start_time, utc=True)
            if start_ts.tz is None:
                start_ts = start_ts.tz_localize("UTC")
            else:
                start_ts = start_ts.tz_convert("UTC")
            filtered_data = filtered_data[filtered_data.index >= start_ts]

        if end_time:
            end_ts = pd.to_datetime(end_time, utc=True)
            if end_ts.tz is None:
                end_ts = end_ts.tz_localize("UTC")
            else:
                end_ts = end_ts.tz_convert("UTC")
            filtered_data = filtered_data[filtered_data.index <= end_ts]

        if limit:
            filtered_data = filtered_data.tail(limit)

        return filtered_data if not filtered_data.empty else None

    def __getattr__(self, name: str):
        return getattr(self.strategy, name)
