"""Shared fixtures for backtest results tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.results.hash import compute_backtest_hash


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


@pytest.fixture
def sample_trades():
    """Sample trades DataFrame for testing."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "entry_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-15", tz="UTC"),
            ],
            "exit_time": [
                pd.Timestamp("2024-01-10", tz="UTC"),
                pd.Timestamp("2024-01-20", tz="UTC"),
            ],
            "entry_price": [100.0, 105.0],
            "exit_price": [105.0, 110.0],
            "shares": [100.0, 100.0],
            "gross_pnl": [500.0, 500.0],
        }
    )


@pytest.fixture
def standard_backtest_params():
    """Standard backtest parameters for hash computation."""
    return {
        "strategy_params": {"short_window": 10},
        "execution_config": ExecutionConfig(),
        "start_date": pd.Timestamp("2024-01-01", tz="UTC"),
        "end_date": pd.Timestamp("2024-01-31", tz="UTC"),
        "step_frequency": "daily",
        "database": "test_db",
        "tickers": ["AAPL"],
        "capital_per_trade": 10000.0,
        "risk_free_rate": 0.04,
        "walk_forward": False,
        "train_days": None,
        "test_days": None,
        "train_split": None,
        "filter_params": None,
    }


@pytest.fixture
def standard_backtest_hash_id(standard_backtest_params):
    """Compute hash_id for standard backtest parameters."""
    return compute_backtest_hash(
        strategy_params=standard_backtest_params["strategy_params"],
        execution_config=standard_backtest_params["execution_config"],
        start_date=standard_backtest_params["start_date"],
        end_date=standard_backtest_params["end_date"],
        step_frequency=standard_backtest_params["step_frequency"],
        database=standard_backtest_params["database"],
        tickers=standard_backtest_params["tickers"],
        capital_per_trade=standard_backtest_params["capital_per_trade"],
        risk_free_rate=standard_backtest_params["risk_free_rate"],
        walk_forward=standard_backtest_params["walk_forward"],
        train_days=standard_backtest_params["train_days"],
        test_days=standard_backtest_params["test_days"],
        train_split=standard_backtest_params["train_split"],
        filter_params=standard_backtest_params["filter_params"],
    )


@pytest.fixture
def walk_forward_backtest_params():
    """Walk-forward backtest parameters for hash computation."""
    return {
        "strategy_params": {},
        "execution_config": ExecutionConfig(),
        "start_date": pd.Timestamp("2024-01-01", tz="UTC"),
        "end_date": pd.Timestamp("2024-01-31", tz="UTC"),
        "step_frequency": "daily",
        "database": "debug",
        "tickers": ["AAPL"],
        "capital_per_trade": 10000.0,
        "risk_free_rate": 0.04,
        "walk_forward": True,
        "train_days": 90,
        "test_days": 30,
        "train_split": None,
        "filter_params": None,
    }


@pytest.fixture
def walk_forward_backtest_hash_id(walk_forward_backtest_params):
    """Compute hash_id for walk-forward backtest parameters."""
    return compute_backtest_hash(
        strategy_params=walk_forward_backtest_params["strategy_params"],
        execution_config=walk_forward_backtest_params["execution_config"],
        start_date=walk_forward_backtest_params["start_date"],
        end_date=walk_forward_backtest_params["end_date"],
        step_frequency=walk_forward_backtest_params["step_frequency"],
        database=walk_forward_backtest_params["database"],
        tickers=walk_forward_backtest_params["tickers"],
        capital_per_trade=walk_forward_backtest_params["capital_per_trade"],
        risk_free_rate=walk_forward_backtest_params["risk_free_rate"],
        walk_forward=walk_forward_backtest_params["walk_forward"],
        train_days=walk_forward_backtest_params["train_days"],
        test_days=walk_forward_backtest_params["test_days"],
        train_split=walk_forward_backtest_params["train_split"],
        filter_params=walk_forward_backtest_params["filter_params"],
    )
