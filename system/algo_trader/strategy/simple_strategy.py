from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import pandas as pd


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Strategy(ABC):
    def __init__(self, side: Side = Side.LONG, window: int | None = None, **_: Any) -> None:
        self.side = side
        self.window = window
        self.strategy_name = type(self).__name__

    @classmethod
    def add_arguments(cls, parser) -> None:
        parser.add_argument(
            "--side",
            type=str,
            choices=[Side.LONG.value, Side.SHORT.value],
            default=Side.LONG.value,
            help="Trade side (LONG or SHORT)",
        )
        parser.add_argument(
            "--window",
            type=int,
            default=None,
            help="Optional lookback window in bars (overrides engine default if set)",
        )

    @abstractmethod
    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        raise NotImplementedError


