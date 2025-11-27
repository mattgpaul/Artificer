from __future__ import annotations

from typing import Any

import pandas as pd

from system.algo_trader.strategy.strategy import Side, Strategy
from system.algo_trader.strategy.studies.base_study import StudySpec
from system.algo_trader.strategy.studies.moving_average.exponential_moving_average import (
    ExponentialMovingAverage,
)

class EMACrossover(Strategy):
    def __init__(
        self,
        short: int = 3,
        long: int = 8,
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
        self.ema_study = ExponentialMovingAverage()

    @classmethod
    def add_arguments(cls, parser) -> None:
        Strategy.add_arguments(parser)
        parser.add_argument(
            "--short",
            type=int,
            default=3,
            help="Short-term EMA window period (default: 3)",
        )
        parser.add_argument(
            "--long",
            type=int,
            default=8,
            help="Long-term EMA window period (default: 8)",
        )

    def get_study_specs(self) -> list[StudySpec]:
        return [
            StudySpec(
                name="ema_short",
                study=self.ema_study,
                params={"window": self.short, "column": "close"},
                min_bars=self.short,
            ),
            StudySpec(
                name="ema_long",
                study=self.ema_study,
                params={"window": self.long, "column": "close"},
                min_bars=self.long,
            ),
        ]

    def _calculate_emas(
        self, ohlcv_data: pd.DataFrame, ticker: str
    ) -> tuple[pd.Series, pd.Series] | tuple[None, None]:
        ema_short = self.ema_study.compute(
            ohlcv_data=ohlcv_data,
            window=self.short,
            ticker=ticker,
            column="close",
        )
        if ema_short is None:
            return None, None

        ema_long = self.ema_study.compute(
            ohlcv_data=ohlcv_data,
            window=self.long,
            ticker=ticker,
            column="close",
        )
        if ema_long is None:
            return None, None

        return ema_short, ema_long

    def _last_crossover_state(
        self, ema_short: pd.Series, ema_long: pd.Series
    ) -> tuple[float, float] | None:
        if len(ema_short) < 2 or len(ema_long) < 2:
            return None
        diff = ema_short - ema_long
        prev = float(diff.iloc[-2])
        curr = float(diff.iloc[-1])
        return prev, curr

    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        ema_short, ema_long = self._calculate_emas(ohlcv_data, ticker)
        if ema_short is None:
            return pd.DataFrame()

        state = self._last_crossover_state(ema_short, ema_long)
        if state is None:
            return pd.DataFrame()
        prev, curr = state

        if prev < 0.0 and curr > 0.0:
            return self._build_price_signal(ohlcv_data)
        return pd.DataFrame()

    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        ema_short, ema_long = self._calculate_emas(ohlcv_data, ticker)
        if ema_short is None:
            return pd.DataFrame()

        state = self._last_crossover_state(ema_short, ema_long)
        if state is None:
            return pd.DataFrame()
        prev, curr = state

        if prev > 0.0 and curr < 0.0:
            return self._build_price_signal(ohlcv_data)
        return pd.DataFrame()