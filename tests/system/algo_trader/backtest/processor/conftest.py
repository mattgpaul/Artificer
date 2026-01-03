"""Shared fixtures for backtest processor tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.engine import BacktestResults


@pytest.fixture
def default_worker_args():
    """Create default worker args tuple with all 23 parameters.

    Returns a tuple matching the signature expected by backtest_ticker_worker:
    (ticker, strategy_type, strategy_params, start_date, end_date, step_frequency,
     database, results_database, execution_config_dict, capital_per_trade,
     risk_free_rate, backtest_id, walk_forward, train_days, test_days,
     train_split, initial_account_value, trade_percentage, filter_pipeline,
     position_manager_config_name, portfolio_manager_config_name, filter_config_dict,
     hash_id_local)
    """
    return (
        "AAPL",
        "SMACrossover",
        {"short_window": 10, "long_window": 20},
        pd.Timestamp("2024-01-01", tz="UTC"),
        pd.Timestamp("2024-01-31", tz="UTC"),
        "daily",
        "test_db",
        "debug",
        {"slippage_bps": 5.0, "commission_per_share": 0.005},
        10000.0,
        0.04,
        "test-backtest-id",
        False,
        None,
        None,
        None,
        None,
        None,
        None,  # filter_pipeline
        None,  # position_manager_config_name
        None,  # portfolio_manager_config_name
        None,  # filter_config_dict
        None,  # hash_id_local
    )


@pytest.fixture
def worker_args_with_account_tracking():
    """Create worker args tuple with account tracking parameters."""
    return (
        "AAPL",
        "SMACrossover",
        {"short_window": 10, "long_window": 20},
        pd.Timestamp("2024-01-01", tz="UTC"),
        pd.Timestamp("2024-01-31", tz="UTC"),
        "daily",
        "debug",
        "debug",
        {"slippage_bps": 5.0, "commission_per_share": 0.005},
        10000.0,
        0.04,
        "test-backtest-id",
        False,
        None,
        None,
        None,
        50000.0,  # initial_account_value
        0.10,  # trade_percentage
        None,  # filter_pipeline
        None,  # position_manager_config_name
        None,  # portfolio_manager_config_name
        None,  # filter_config_dict
        None,  # hash_id_local
    )


@pytest.fixture
def worker_args_with_walk_forward():
    """Create worker args tuple with walk-forward parameters."""
    return (
        "AAPL",
        "SMACrossover",
        {"short_window": 10, "long_window": 20},
        pd.Timestamp("2024-01-01", tz="UTC"),
        pd.Timestamp("2024-12-31", tz="UTC"),
        "daily",
        "debug",
        "debug",
        {"slippage_bps": 5.0, "commission_per_share": 0.005},
        10000.0,
        0.04,
        "test-backtest-id",
        True,  # walk_forward
        90,  # train_days
        30,  # test_days
        None,  # train_split
        None,  # initial_account_value
        None,  # trade_percentage
        None,  # filter_pipeline
        None,  # position_manager_config_name
        None,  # portfolio_manager_config_name
        None,  # filter_config_dict
        None,  # hash_id_local
    )


@pytest.fixture
def mock_strategy():
    """Create a mock strategy instance."""
    mock = MagicMock()
    mock.close = MagicMock()
    return mock


@pytest.fixture
def mock_backtest_engine():
    """Create a mock BacktestEngine instance."""
    mock_engine = MagicMock()
    mock_engine.influx_client = MagicMock()
    mock_engine.influx_client.close = MagicMock()
    return mock_engine


@pytest.fixture
def mock_backtest_results_with_trades():
    """Create mock BacktestResults with trades."""
    results = BacktestResults()
    results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
    results.metrics = {"total_trades": 1}
    results.strategy_name = "SMACrossover"
    results.studies = pd.DataFrame()
    return results


@pytest.fixture
def mock_backtest_results_empty():
    """Create mock BacktestResults with empty trades."""
    results = BacktestResults()
    results.trades = pd.DataFrame()
    results.metrics = {}
    results.strategy_name = "SMACrossover"
    results.studies = pd.DataFrame()
    return results


@pytest.fixture
def mock_dependencies_worker():
    """Composite fixture for worker tests with all common mocks."""
    with (
        patch(
            "system.algo_trader.backtest.processor.worker.create_strategy_instance"
        ) as mock_create_strategy,
        patch("system.algo_trader.backtest.processor.worker.BacktestEngine") as mock_engine_class,
        patch(
            "system.algo_trader.backtest.processor.worker.write_backtest_results"
        ) as mock_write_results,
        patch(
            "system.algo_trader.backtest.processor.worker.log_backtest_results"
        ) as mock_log_results,
    ):
        yield {
            "create_strategy": mock_create_strategy,
            "engine_class": mock_engine_class,
            "write_results": mock_write_results,
            "log_results": mock_log_results,
        }
