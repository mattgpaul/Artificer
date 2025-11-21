"""Hash computation for backtest configuration.

This module provides functionality to compute deterministic hashes from backtest
configuration parameters for deduplication and result identification.
"""

import hashlib
import json
from typing import Any

import pandas as pd

from system.algo_trader.backtest.core.execution import ExecutionConfig


def compute_backtest_hash(
    strategy_params: dict[str, Any],
    execution_config: ExecutionConfig,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    step_frequency: str,
    database: str,
    tickers: list[str],
    capital_per_trade: float,
    risk_free_rate: float,
    walk_forward: bool = False,
    train_days: int | None = None,
    test_days: int | None = None,
    train_split: float | None = None,
    position_manager_params: dict[str, Any] | None = None,
    filter_params: dict[str, Any] | None = None,
) -> str:
    """Compute deterministic hash from backtest configuration.

    Creates a SHA-256 hash from backtest parameters to uniquely identify
    a backtest configuration. Used for deduplication and result lookup.

    Note: tickers, start_date, end_date, and database are NOT included in the hash
    to allow comparing results across different time periods, tickers, and databases.

    Args:
        strategy_params: Dictionary of strategy parameters.
        execution_config: Execution configuration with slippage and commission.
        start_date: Start date of backtest period (not included in hash).
        end_date: End date of backtest period (not included in hash).
        step_frequency: Frequency for time steps.
        database: Database name used for data access (not included in hash).
        tickers: List of ticker symbols (not included in hash).
        capital_per_trade: Capital allocated per trade.
        risk_free_rate: Risk-free rate for Sharpe ratio calculation.
        walk_forward: Whether walk-forward analysis is used.
        train_days: Number of training days (if walk-forward).
        test_days: Number of test days (if walk-forward).
        train_split: Training split ratio (if walk-forward).
        position_manager_params: Optional dictionary of position manager configuration.
        filter_params: Optional dictionary of filter configuration.

    Returns:
        16-character hexadecimal hash string representing the configuration.
    """
    args_dict = {
        "strategy_params": strategy_params,
        "execution": {
            "slippage_bps": execution_config.slippage_bps,
            "commission_per_share": execution_config.commission_per_share,
            "use_limit_orders": execution_config.use_limit_orders,
            "fill_delay_minutes": execution_config.fill_delay_minutes,
        },
        "backtest": {
            "step_frequency": step_frequency,
        },
        "capital_per_trade": capital_per_trade,
        "risk_free_rate": risk_free_rate,
        "walk_forward": walk_forward,
        "train_days": train_days,
        "test_days": test_days,
        "train_split": train_split,
    }
    if position_manager_params is not None:
        args_dict["position_manager"] = position_manager_params
    if filter_params is not None:
        args_dict["filters"] = filter_params
    args_json = json.dumps(args_dict, sort_keys=True, default=str)
    return hashlib.sha256(args_json.encode()).hexdigest()[:16]
