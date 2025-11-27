"""Shared fixtures for filter tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.filters.core import FilterContext


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("infrastructure.logging.logger.get_logger") as mock_logger_func:
        mock_logger_instance = MagicMock()
        mock_logger_func.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def sample_signal():
    """Fixture providing sample signal dictionary."""
    return {
        "ticker": "AAPL",
        "signal_time": "2024-01-01T10:00:00Z",
        "signal_type": "buy",
        "price": 150.0,
        "confidence": 0.8,
    }


@pytest.fixture
def sample_ohlcv_data():
    """Fixture providing sample OHLCV data for testing."""
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    return pd.DataFrame(
        {
            "open": [100.0] * 30,
            "high": [105.0] * 30,
            "low": [95.0] * 30,
            "close": list(range(100, 130)),
            "volume": [1000000] * 30,
        },
        index=dates,
    )


@pytest.fixture
def sample_ohlcv_by_ticker(sample_ohlcv_data):
    """Fixture providing OHLCV data by ticker."""
    return {"AAPL": sample_ohlcv_data}


@pytest.fixture
def filter_context(sample_signal, sample_ohlcv_by_ticker):
    """Fixture providing FilterContext with sample data."""
    return FilterContext(sample_signal, sample_ohlcv_by_ticker)


@pytest.fixture
def empty_filter_context():
    """Fixture providing FilterContext with empty OHLCV data."""
    signal = {"ticker": "AAPL", "signal_time": "2024-01-01T10:00:00Z"}
    return FilterContext(signal, {})
