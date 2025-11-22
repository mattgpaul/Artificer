"""Shared fixtures for backtest results tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("infrastructure.logging.logger.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_queue_broker():
    """Mock QueueBroker for ResultsWriter tests."""
    with patch("system.algo_trader.backtest.results.writer.QueueBroker") as mock_broker_class:
        mock_broker = MagicMock()
        mock_broker.enqueue.return_value = True
        mock_broker_class.return_value = mock_broker
        yield mock_broker


@pytest.fixture
def sample_studies_data():
    """Sample studies DataFrame for testing."""
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [99.0, 100.0, 101.0],
            "close": [104.0, 105.0, 106.0],
            "volume": [1000000, 1100000, 1200000],
            "sma_10": [102.0, 103.0, 104.0],
            "sma_20": [101.0, 102.0, 103.0],
        },
        index=[
            pd.Timestamp("2024-01-05", tz="UTC"),
            pd.Timestamp("2024-01-06", tz="UTC"),
            pd.Timestamp("2024-01-07", tz="UTC"),
        ],
    )


@pytest.fixture
def sample_studies_data_minimal():
    """Minimal studies DataFrame for testing."""
    return pd.DataFrame(
        {
            "close": [100.0, 101.0],
            "sma_10": [99.0, 100.0],
        },
        index=[
            pd.Timestamp("2024-01-05", tz="UTC"),
            pd.Timestamp("2024-01-06", tz="UTC"),
        ],
    )


@pytest.fixture
def sample_studies_data_single():
    """Single-row studies DataFrame for testing."""
    return pd.DataFrame(
        {
            "close": [100.0],
            "sma_10": [99.0],
        },
        index=[pd.Timestamp("2024-01-05", tz="UTC")],
    )


@pytest.fixture
def execution_config():
    """Create ExecutionConfig for testing."""
    return ExecutionConfig(
        slippage_bps=5.0,
        commission_per_share=0.005,
        use_limit_orders=False,
        fill_delay_minutes=0,
    )

