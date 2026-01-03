"""Shared fixtures for portfolio manager tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.portfolio_manager.portfolio_manager import (
    PortfolioManager,
)
from system.algo_trader.strategy.portfolio_manager.rules.base import (
    PortfolioRulePipeline,
)


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("infrastructure.logging.logger.get_logger") as mock_logger_func:
        mock_logger_instance = MagicMock()
        mock_logger_func.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def make_ohlcv():
    """Create OHLCV data for a ticker."""

    def _make_ohlcv(days: list[str], ticker: str = "TEST") -> dict[str, pd.DataFrame]:
        idx = pd.to_datetime(days, utc=True)
        df = pd.DataFrame(
            {
                "open": [100.0 for _ in days],
                "high": [101.0 for _ in days],
                "low": [99.0 for _ in days],
                "close": [100.0 for _ in days],
                "volume": [1000 for _ in days],
            },
            index=idx,
        )
        return {ticker: df}

    return _make_ohlcv


@pytest.fixture
def empty_pipeline():
    """Create an empty PortfolioRulePipeline."""
    return PortfolioRulePipeline(rules=[])


@pytest.fixture
def sample_executions():
    """Create sample execution DataFrame."""
    return pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "strategy": "SMA",
                "side": "LONG",
                "action": "buy_to_open",
                "price": 10.0,
                "shares": 10.0,
                "signal_time": pd.Timestamp("2020-01-01", tz="UTC"),
                "hash": "hash1",
            },
            {
                "ticker": "TEST",
                "strategy": "SMA",
                "side": "LONG",
                "action": "sell_to_close",
                "price": 11.0,
                "shares": 10.0,
                "signal_time": pd.Timestamp("2020-01-02", tz="UTC"),
                "hash": "hash1",
            },
        ]
    )


@pytest.fixture
def sample_executions_insufficient_capital():
    """Create sample execution DataFrame with insufficient capital."""
    return pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "strategy": "SMA",
                "side": "LONG",
                "action": "buy_to_open",
                "price": 10.0,
                "shares": 1000.0,
                "signal_time": pd.Timestamp("2020-01-01", tz="UTC"),
                "hash": "hash1",
            },
            {
                "ticker": "TEST",
                "strategy": "SMA",
                "side": "LONG",
                "action": "sell_to_close",
                "price": 11.0,
                "shares": 1000.0,
                "signal_time": pd.Timestamp("2020-01-02", tz="UTC"),
                "hash": "hash1",
            },
        ]
    )


@pytest.fixture
def default_portfolio_manager(empty_pipeline):
    """Create a PortfolioManager with default settings."""
    return PortfolioManager(
        pipeline=empty_pipeline,
        initial_account_value=100000.0,
        settlement_lag_trading_days=2,
    )


@pytest.fixture
def portfolio_manager_insufficient_capital(empty_pipeline):
    """Create a PortfolioManager with insufficient capital."""
    return PortfolioManager(
        pipeline=empty_pipeline,
        initial_account_value=50.0,
        settlement_lag_trading_days=2,
    )
