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
    with patch("infrastructure.logging.logger.get_logger") as mock_logger_func:
        mock_logger_instance = MagicMock()
        mock_logger_func.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data with sufficient length for SMA calculations."""
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
def sample_ohlcv_data_crossover():
    """Sample OHLCV data designed to create SMA crossover scenarios."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D", tz=timezone.utc)
    # Create data where short SMA crosses above long SMA around index 20
    # First 15: declining prices (short SMA below long)
    # Next 15: rising prices (short SMA crosses above long)
    close_prices = []
    for i in range(30):
        if i < 15:
            close_prices.append(100.0 - i * 0.5)  # Declining
        else:
            close_prices.append(92.5 + (i - 15) * 1.0)  # Rising

    return pd.DataFrame(
        {
            "open": [p - 0.5 for p in close_prices],
            "high": [p + 0.5 for p in close_prices],
            "low": [p - 1.0 for p in close_prices],
            "close": close_prices,
            "volume": [1000000] * 30,
        },
        index=dates,
    )


@pytest.fixture
def sample_ohlcv_data_empty():
    """Empty OHLCV DataFrame."""
    return pd.DataFrame()


@pytest.fixture
def sample_ohlcv_data_missing_close():
    """OHLCV data missing 'close' column."""
    dates = pd.date_range("2024-01-01", periods=10, freq="D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "open": [100.0] * 10,
            "high": [105.0] * 10,
            "low": [95.0] * 10,
            "volume": [1000000] * 10,
        },
        index=dates,
    )


@pytest.fixture
def sample_ohlcv_data_insufficient():
    """OHLCV data with insufficient length for SMA calculations."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "open": [100.0] * 5,
            "high": [105.0] * 5,
            "low": [95.0] * 5,
            "close": [100.0] * 5,
            "volume": [1000000] * 5,
        },
        index=dates,
    )
