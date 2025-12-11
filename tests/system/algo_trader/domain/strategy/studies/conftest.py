"""Shared fixtures for study tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

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
def empty_ohlcv_data():
    """Fixture providing empty OHLCV DataFrame."""
    return pd.DataFrame()


@pytest.fixture
def ohlcv_data_missing_close():
    """Fixture providing OHLCV data missing 'close' column."""
    dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
    return pd.DataFrame(
        {
            "open": [100.0] * 10,
            "high": [105.0] * 10,
            "low": [95.0] * 10,
            "volume": [1000000] * 10,
        },
        index=dates,
    )
