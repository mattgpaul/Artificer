"""Shared fixtures for strategy tests.

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
    with patch("infrastructure.logging.logger.get_logger") as mock_infra_logger:
        mock_logger_instance = MagicMock()
        mock_infra_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_args():
    """Mock command-line arguments for executor tests."""
    args = MagicMock()
    args.strategy = "sma-crossover"
    args.short = 10
    args.long = 20
    args.database = "test-database"
    args.threading = False
    args.limit = None
    args.write = False
    args.lookback = 90
    args.journal = False
    args.capital = 10000.0
    args.risk_free_rate = 0.04
    args.detailed = False
    return args


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "open": [100.0 + i * 0.1 for i in range(50)],
            "high": [101.0 + i * 0.1 for i in range(50)],
            "low": [99.0 + i * 0.1 for i in range(50)],
            "close": [100.5 + i * 0.1 for i in range(50)],
            "volume": [1000000] * 50,
        },
        index=dates,
    )


@pytest.fixture
def sample_signals():
    """Sample signals DataFrame for testing."""
    dates = pd.date_range("2024-01-01", periods=4, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "signal_type": ["buy", "sell", "buy", "sell"],
            "price": [150.0, 155.0, 350.0, 360.0],
            "confidence": [0.85, 0.90, 0.75, 0.80],
            "signal_time": dates,
        },
        index=dates,
    )


@pytest.fixture
def sample_trades():
    """Sample trades DataFrame for formatting tests."""
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
