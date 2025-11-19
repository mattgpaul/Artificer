"""Shared fixtures for backtest processor tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

import pandas as pd
import pytest


@pytest.fixture
def default_worker_args():
    """Create default worker args tuple with all 19 parameters.

    Returns a tuple matching the signature expected by backtest_ticker_worker:
    (ticker, strategy_type, strategy_params, start_date, end_date, step_frequency,
     database, results_database, execution_config_dict, capital_per_trade,
     risk_free_rate, backtest_id, walk_forward, train_days, test_days,
     train_split, initial_account_value, trade_percentage, position_manager_config_dict)
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
        None,  # position_manager_config_dict
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
        None,  # position_manager_config_dict
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
        None,  # position_manager_config_dict
    )
