from __future__ import annotations

from typing import Any

import pandas as pd

from system.algo_trader.strategy.simple_strategy import Side, Strategy


class ExampleSMACross(Strategy):
    def __init__(
        self,
        short: int = 10,
        long: int = 20,
        window: int = 120,
        side: Side = Side.LONG,
        **extra: Any,
    ) -> None:
        super().__init__(side=side, window=window, **extra)
        self.short = short
        self.long = long

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

    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        return pd.DataFrame()

    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        return pd.DataFrame()

