"""Simple Moving Average (SMA) crossover trading strategy.

This module implements a classic SMA crossover strategy that generates buy
signals when the short-term SMA crosses above the long-term SMA, and sell
signals when it crosses below.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from system.algo_trader.strategy.strategy import Side, Strategy
from system.algo_trader.strategy.studies.base_study import StudySpec
from system.algo_trader.strategy.studies.moving_average.simple_moving_average import (
    SimpleMovingAverage,
)


class SMACrossover(Strategy):
    """Simple Moving Average crossover trading strategy.

    Generates buy signals when short-term SMA crosses above long-term SMA,
    and sell signals when short-term SMA crosses below long-term SMA.

    Args:
        short: Short-term SMA window period. Must be less than long and >= 2.
            Defaults to 10.
        long: Long-term SMA window period. Must be greater than short.
            Defaults to 20.
        window: Lookback window in bars. Defaults to 120.
        side: Trade side (LONG or SHORT). Defaults to LONG.
        **extra: Additional keyword arguments passed to base Strategy.

    Raises:
        ValueError: If short >= long or short < 2.
    """

    def __init__(
        self,
        short: int = 10,
        long: int = 20,
        window: int = 120,
        side: Side = Side.LONG,
        **extra: Any,
    ) -> None:
        """Initialize SMACrossover strategy.

        Args:
            short: Short-term SMA window period. Must be less than long and >= 2.
                Defaults to 10.
            long: Long-term SMA window period. Must be greater than short.
                Defaults to 20.
            window: Lookback window in bars. Defaults to 120.
            side: Trade side (LONG or SHORT). Defaults to LONG.
            **extra: Additional keyword arguments passed to base Strategy.

        Raises:
            ValueError: If short >= long or short < 2.
        """
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
        """Add strategy-specific arguments to argument parser.

        Args:
            parser: ArgumentParser instance to add arguments to.
        """
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

    def get_study_specs(self) -> list[StudySpec]:
        """Get study specifications for this strategy.

        Returns a list of StudySpec objects defining the technical studies
        (indicators) used by this strategy. For SMA crossover, this includes
        both short-term and long-term SMA studies.

        Returns:
            List of StudySpec objects defining the studies to compute.
        """
        return [
            StudySpec(
                name="sma_short",
                study=self.sma_study,
                params={"window": self.short, "column": "close"},
                min_bars=self.short,
            ),
            StudySpec(
                name="sma_long",
                study=self.sma_study,
                params={"window": self.long, "column": "close"},
                min_bars=self.long,
            ),
        ]

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

    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate buy signals when short SMA crosses above long SMA.

        Args:
            ohlcv_data: OHLCV DataFrame for analysis.
            ticker: Ticker symbol.

        Returns:
            DataFrame with buy signals (empty if no crossover detected).
        """
        sma_short, sma_long = self._calculate_smas(ohlcv_data, ticker)
        if sma_short is None:
            return pd.DataFrame()

        state = self._last_crossover_state(sma_short, sma_long)
        if state is None:
            return pd.DataFrame()
        prev, curr = state

        if prev < 0.0 and curr > 0.0:
            return self._build_price_signal(ohlcv_data)
        return pd.DataFrame()

    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate sell signals when short SMA crosses below long SMA.

        Args:
            ohlcv_data: OHLCV DataFrame for analysis.
            ticker: Ticker symbol.

        Returns:
            DataFrame with sell signals (empty if no crossover detected).
        """
        sma_short, sma_long = self._calculate_smas(ohlcv_data, ticker)
        if sma_short is None:
            return pd.DataFrame()

        state = self._last_crossover_state(sma_short, sma_long)
        if state is None:
            return pd.DataFrame()
        prev, curr = state

        if prev > 0.0 and curr < 0.0:
            return self._build_price_signal(ohlcv_data)
        return pd.DataFrame()
