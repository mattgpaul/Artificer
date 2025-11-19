"""Shared fixtures for position_manager tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from datetime import timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.position_manager.position_manager import (
    PositionManagerConfig,
)


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("infrastructure.logging.logger.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def default_config():
    """Create default PositionManagerConfig."""
    return PositionManagerConfig(allow_scale_in=False)


@pytest.fixture
def scale_in_config():
    """Create PositionManagerConfig with scale_in enabled."""
    return PositionManagerConfig(allow_scale_in=True)


@pytest.fixture
def sample_signals_long_entry_exit():
    """Sample signals DataFrame with LONG entry and exit."""
    dates = pd.date_range("2024-01-01", periods=4, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "signal_type": ["buy", "sell", "buy", "sell"],
            "signal_time": dates,
            "price": [150.0, 155.0, 350.0, 360.0],
            "side": ["LONG", "LONG", "LONG", "LONG"],
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_short_entry_exit():
    """Sample signals DataFrame with SHORT entry and exit."""
    dates = pd.date_range("2024-01-01", periods=4, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "signal_type": ["sell", "buy", "sell", "buy"],
            "signal_time": dates,
            "price": [150.0, 145.0, 350.0, 340.0],
            "side": ["SHORT", "SHORT", "SHORT", "SHORT"],
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_multiple_entries():
    """Sample signals DataFrame with multiple entry attempts (should be filtered)."""
    dates = pd.date_range("2024-01-01", periods=5, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL", "AAPL", "AAPL"],
            "signal_type": ["buy", "buy", "buy", "sell", "buy"],
            "signal_time": dates,
            "price": [150.0, 151.0, 152.0, 155.0, 156.0],
            "side": ["LONG", "LONG", "LONG", "LONG", "LONG"],
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_exit_without_entry():
    """Sample signals DataFrame with exit signal before entry (should be filtered)."""
    dates = pd.date_range("2024-01-01", periods=3, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "signal_type": ["sell", "buy", "sell"],
            "signal_time": dates,
            "price": [150.0, 151.0, 155.0],
            "side": ["LONG", "LONG", "LONG"],
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_no_time_column():
    """Sample signals DataFrame without signal_time column."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_type": ["buy", "sell"],
            "price": [150.0, 155.0],
            "side": ["LONG", "LONG"],
        },
        index=[0, 1],
    )


@pytest.fixture
def sample_ohlcv_by_ticker():
    """Sample OHLCV data by ticker."""
    dates = pd.date_range("2024-01-01", periods=10, freq="1D", tz=timezone.utc)
    return {
        "AAPL": pd.DataFrame(
            {
                "open": [150.0] * 10,
                "high": [155.0] * 10,
                "low": [145.0] * 10,
                "close": [152.0] * 10,
                "volume": [1000000] * 10,
            },
            index=dates,
        ),
        "MSFT": pd.DataFrame(
            {
                "open": [350.0] * 10,
                "high": [360.0] * 10,
                "low": [340.0] * 10,
                "close": [355.0] * 10,
                "volume": [2000000] * 10,
            },
            index=dates,
        ),
    }
