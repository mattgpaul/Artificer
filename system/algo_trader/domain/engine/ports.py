"""Port interfaces for the trading engine.

Defines abstract interfaces (ports) that the engine depends on, allowing
different implementations for backtest, paper trading, and live trading.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Protocol

import pandas as pd


class MarketDataFeed(Protocol):
    """Protocol for market data feeds.

    Implementations can provide historical data (backtest), simulated live data
    (paper trading), or real-time data (live trading).
    """

    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        frequency: str = "1d",
    ) -> pd.DataFrame:
        """Get OHLCV data for a symbol in a time range.

        Args:
            symbol: Trading symbol.
            start: Start datetime.
            end: End datetime.
            frequency: Data frequency (e.g., '1d', '1h', '1m').

        Returns:
            DataFrame with OHLCV data.
        """
        ...


class OrderExecutor(Protocol):
    """Protocol for order execution.

    Implementations can simulate execution (backtest/paper) or execute real
    orders (live trading).
    """

    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        quantity: float,
        order_type: str,
        **kwargs: Any,
    ) -> str:
        """Submit an order.

        Args:
            symbol: Trading symbol.
            quantity: Order quantity.
            order_type: Order type (e.g., 'market', 'limit').
            **kwargs: Additional order parameters.

        Returns:
            Order ID.
        """
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel.

        Returns:
            True if cancellation was successful.
        """
        ...


class TimeProvider(Protocol):
    """Protocol for time management.

    Allows different time progression strategies: historical stepping
    (backtest), simulated real-time (paper), or wall-clock time (live).
    """

    @abstractmethod
    def now(self) -> datetime:
        """Get current time.

        Returns:
            Current datetime according to this provider.
        """
        ...

    @abstractmethod
    def advance(self, delta: Any) -> None:
        """Advance time by a delta.

        Args:
            delta: Time delta to advance (timedelta, or step count for backtest).
        """
        ...


class PortfolioRepository(Protocol):
    """Protocol for portfolio state persistence.

    Allows storing and retrieving portfolio state for different execution modes.
    """

    @abstractmethod
    def save_state(self, state: dict[str, Any]) -> None:
        """Save portfolio state.

        Args:
            state: Portfolio state dictionary.
        """
        ...

    @abstractmethod
    def load_state(self) -> dict[str, Any] | None:
        """Load portfolio state.

        Returns:
            Portfolio state dictionary, or None if no state exists.
        """
        ...


class JournalWriter(Protocol):
    """Protocol for trade journal writing.

    Allows different journal implementations for different execution modes.
    """

    @abstractmethod
    def record_trade(self, trade: dict[str, Any]) -> None:
        """Record a trade.

        Args:
            trade: Trade data dictionary.
        """
        ...

    @abstractmethod
    def record_signal(self, signal: dict[str, Any]) -> None:
        """Record a trading signal.

        Args:
            signal: Signal data dictionary.
        """
        ...
