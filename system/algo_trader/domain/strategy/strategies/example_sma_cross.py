"""Example SMA crossover strategy for testing and demonstration.

This module provides a simple example strategy implementation that demonstrates
the Strategy interface without actual signal generation logic.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from system.algo_trader.domain.strategy.strategy import Side, Strategy


class ExampleSMACross(Strategy):
    """Example SMA crossover strategy for testing and demonstration.

    This strategy implements the Strategy interface but does not generate
    actual trading signals. It is intended for testing and as a template
    for implementing real strategies.

    Args:
        short: Short-term SMA window period. Defaults to 10.
        long: Long-term SMA window period. Defaults to 20.
        window: Lookback window in bars. Defaults to 120.
        side: Trade side (LONG or SHORT). Defaults to LONG.
        **extra: Additional keyword arguments passed to base Strategy.
    """

    def __init__(
        self,
        short: int = 10,
        long: int = 20,
        window: int = 120,
        side: Side = Side.LONG,
        **extra: Any,
    ) -> None:
        """Initialize ExampleSMACross strategy.

        Args:
            short: Short-term SMA window period. Defaults to 10.
            long: Long-term SMA window period. Defaults to 20.
            window: Lookback window in bars. Defaults to 120.
            side: Trade side (LONG or SHORT). Defaults to LONG.
            **extra: Additional keyword arguments passed to base Strategy.
        """
        super().__init__(side=side, window=window, **extra)
        self.short = short
        self.long = long

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

    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate buy signals (example implementation returns empty).

        Args:
            ohlcv_data: OHLCV DataFrame for analysis.
            ticker: Ticker symbol.

        Returns:
            Empty DataFrame (example implementation).
        """
        return pd.DataFrame()

    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate sell signals (example implementation returns empty).

        Args:
            ohlcv_data: OHLCV DataFrame for analysis.
            ticker: Ticker symbol.

        Returns:
            Empty DataFrame (example implementation).
        """
        return pd.DataFrame()
