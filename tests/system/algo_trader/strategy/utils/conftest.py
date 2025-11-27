"""Shared fixtures for strategy utils tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from datetime import timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("system.algo_trader.backtest.cli_utils.get_logger") as mock_logger_func:
        mock_logger_instance = MagicMock()
        mock_logger_func.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_influx_client():
    """Fixture to mock MarketDataInflux client for cli_utils tests."""
    with patch("system.algo_trader.backtest.cli_utils.MarketDataInflux") as mock_influx_class:
        mock_client = MagicMock()
        mock_influx_class.return_value = mock_client
        yield {"class": mock_influx_class, "instance": mock_client}


@pytest.fixture
def mock_tickers_class():
    """Fixture to mock SEC Tickers class for cli_utils tests."""
    with patch("system.algo_trader.backtest.cli_utils.Tickers") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield {"class": mock_class, "instance": mock_instance}


@pytest.fixture
def mock_get_sp500():
    """Fixture to mock get_sp500_tickers function for cli_utils tests."""
    with patch("system.algo_trader.backtest.cli_utils.get_sp500_tickers") as mock_func:
        yield mock_func


@pytest.fixture
def sample_signals():
    """Sample signals DataFrame for cli_utils formatting tests."""
    dates = pd.date_range("2024-01-01", periods=5, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT", "GOOGL"],
            "signal_type": ["buy", "sell", "buy", "sell", "buy"],
            "price": [150.0, 155.0, 350.0, 360.0, 2800.0],
            "confidence": [0.85, 0.90, 0.75, 0.80, 0.70],
            "signal_time": dates,
        },
        index=dates,
    )


@pytest.fixture
def sample_trades():
    """Sample trades DataFrame for cli_utils formatting tests."""
    return pd.DataFrame(
        {
            "entry_time": [
                pd.Timestamp("2024-01-01 10:00:00", tz=timezone.utc),
                pd.Timestamp("2024-01-05 11:00:00", tz=timezone.utc),
                pd.Timestamp("2024-01-10 09:30:00", tz=timezone.utc),
            ],
            "exit_time": [
                pd.Timestamp("2024-01-03 15:00:00", tz=timezone.utc),
                pd.Timestamp("2024-01-08 14:00:00", tz=timezone.utc),
                pd.Timestamp("2024-01-15 16:00:00", tz=timezone.utc),
            ],
            "entry_price": [150.0, 155.0, 148.0],
            "exit_price": [155.0, 152.0, 160.0],
            "shares": [100.0, 100.0, 100.0],
            "gross_pnl": [500.0, -300.0, 800.0],
            "gross_pnl_pct": [3.33, -1.94, 8.11],
        }
    )
