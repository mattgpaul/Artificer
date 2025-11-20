from __future__ import annotations

from typing import Any

import pandas as pd

from system.algo_trader.strategy.simple_strategy import Side, Strategy
from system.algo_trader.strategy.utils.studies.moving_average.simple_moving_average import (
    SimpleMovingAverage,
)


class SMACrossover(Strategy):
    def __init__(
        self,
        short: int = 10,
        long: int = 20,
        window: int = 120,
        side: Side = Side.LONG,
        **extra: Any,
    ) -> None:
        if short >= long:
            raise ValueError(f"short ({short}) must be less than long ({long})")
        if short < 2:
            raise ValueError(f"short must be at least 2, got {short}")

        super().__init__(side=side, window=window, **extra)
        self.short = short
        self.long = long
        self.sma_study = SimpleMovingAverage()

    @classmethod
    def add_arguments(cls, parser) -> None:
        Strategy.add_arguments(parser)
        parser.add_argument(
            "--short",
            type=int,
            default=10,
            help="Short-term SMA window period (default: 10)",
        )
        parser.add_argument(
            "--long",
            type=int,
            default=20,
            help="Long-term SMA window period (default: 20)",
        )

    def _calculate_smas(
        self, ohlcv_data: pd.DataFrame, ticker: str
    ) -> tuple[pd.Series, pd.Series] | tuple[None, None]:
        sma_short = self.sma_study.compute(
            ohlcv_data=ohlcv_data,
            window=self.short,
            ticker=ticker,
            column="close",
        )
        if sma_short is None:
            return None, None

        sma_long = self.sma_study.compute(
            ohlcv_data=ohlcv_data,
            window=self.long,
            ticker=ticker,
            column="close",
        )
        if sma_long is None:
            return None, None

        return sma_short, sma_long

    def _last_crossover_state(
        self, sma_short: pd.Series, sma_long: pd.Series
    ) -> tuple[float, float] | None:
        if len(sma_short) < 2 or len(sma_long) < 2:
            return None
        diff = sma_short - sma_long
        prev = float(diff.iloc[-2])
        curr = float(diff.iloc[-1])
        return prev, curr

    def _build_signal(self, ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        if ohlcv_data.empty or "close" not in ohlcv_data.columns:
            return pd.DataFrame()
        ts = ohlcv_data.index[-1]
        price = float(ohlcv_data["close"].iloc[-1])
        return pd.DataFrame(
            [{"price": round(price, 4)}],
            index=pd.DatetimeIndex([ts]),
        )

    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        sma_short, sma_long = self._calculate_smas(ohlcv_data, ticker)
        if sma_short is None:
            return pd.DataFrame()

        state = self._last_crossover_state(sma_short, sma_long)
        if state is None:
            return pd.DataFrame()
        prev, curr = state

        if prev < 0.0 and curr > 0.0:
            return self._build_signal(ohlcv_data)
        return pd.DataFrame()

    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        sma_short, sma_long = self._calculate_smas(ohlcv_data, ticker)
        if sma_short is None:
            return pd.DataFrame()

        state = self._last_crossover_state(sma_short, sma_long)
        if state is None:
            return pd.DataFrame()
        prev, curr = state

        if prev > 0.0 and curr < 0.0:
            return self._build_signal(ohlcv_data)
        return pd.DataFrame()


