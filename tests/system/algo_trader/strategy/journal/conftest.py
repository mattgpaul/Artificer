"""Shared fixtures for journal tests.

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
def mock_efficiency():
    """Mock calculate_efficiency function."""
    with patch(
        "system.algo_trader.strategy.journal.trade_matching.calculate_efficiency"
    ) as mock_efficiency_func:
        mock_efficiency_func.return_value = 75.0
        yield mock_efficiency_func


@pytest.fixture
def sample_signals_long_entry_exit():
    """Sample signals for LONG entry and exit."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "signal_type": ["buy", "sell"],
            "price": [100.0, 105.0],
            "side": ["LONG", "LONG"],
        }
    )


@pytest.fixture
def sample_signals_short_entry_exit():
    """Sample signals for SHORT entry and exit."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "signal_type": ["sell", "buy"],
            "price": [100.0, 95.0],
            "side": ["SHORT", "SHORT"],
        }
    )
