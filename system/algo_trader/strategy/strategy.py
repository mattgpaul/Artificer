"""Base strategy interface for trading strategies.

This module defines the abstract base class for all trading strategies,
providing a common interface for signal generation and configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from system.algo_trader.strategy.studies.base_study import StudySpec


class Side(str, Enum):
    """Trade side enumeration.

    LONG: Long position (buy to enter, sell to exit).
    SHORT: Short position (sell to enter, buy to exit).
    """

    LONG = "LONG"
    SHORT = "SHORT"


class Strategy(ABC):
    """Abstract base class for trading strategies.

    All trading strategies must inherit from this class and implement the
    buy() and sell() methods to generate trading signals.

    Args:
        side: Trade side (LONG or SHORT). Defaults to LONG.
        window: Optional lookback window in bars. Defaults to None.
        **_: Additional keyword arguments (ignored).
    """

    def __init__(self, side: Side = Side.LONG, window: int | None = None, **_: Any) -> None:
        """Initialize Strategy base class.

        Args:
            side: Trade side (LONG or SHORT). Defaults to LONG.
            window: Optional lookback window in bars. Defaults to None.
            **_: Additional keyword arguments (ignored).
        """
        self.side = side
        self.window = window
        self.strategy_name = type(self).__name__

    @classmethod
    def add_arguments(cls, parser) -> None:
        """Add strategy arguments to argument parser.

        Args:
            parser: ArgumentParser instance to add arguments to.
        """
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
        """Generate buy signals from OHLCV data.

        Args:
            ohlcv_data: OHLCV DataFrame for analysis.
            ticker: Ticker symbol.

        Returns:
            DataFrame with buy signals. Must have 'price' column and
            DatetimeIndex for signal_time. Empty DataFrame if no signals.
        """
        raise NotImplementedError

    @abstractmethod
    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate sell signals from OHLCV data.

        Args:
            ohlcv_data: OHLCV DataFrame for analysis.
            ticker: Ticker symbol.

        Returns:
            DataFrame with sell signals. Must have 'price' column and
            DatetimeIndex for signal_time. Empty DataFrame if no signals.
        """
        raise NotImplementedError

    def get_study_specs(self) -> list[StudySpec]:
        """Get study specifications for persistence during backtests.

        Returns:
            List of StudySpec instances describing which studies should be
            captured and persisted. Default implementation returns empty list.
        """
        return []

    def _build_price_signal(self, ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        """Build a price signal DataFrame from the latest OHLCV bar.

        Creates a single-row DataFrame with the latest timestamp and closing price.
        Returns empty DataFrame if input is empty or missing 'close' column.

        Args:
            ohlcv_data: OHLCV DataFrame for analysis.

        Returns:
            DataFrame with 'price' column and DatetimeIndex, or empty DataFrame
            if input is invalid.
        """
        if ohlcv_data.empty or "close" not in ohlcv_data.columns:
            return pd.DataFrame()
        ts = ohlcv_data.index[-1]
        price = float(ohlcv_data["close"].iloc[-1])
        return pd.DataFrame(
            [{"price": round(price, 4)}],
            index=pd.DatetimeIndex([ts]),
        )
