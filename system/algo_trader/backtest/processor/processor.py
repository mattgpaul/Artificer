"""Backtest processor for orchestrating backtest execution.

This module provides functionality to process multiple tickers through backtest
execution, supporting both parallel and sequential processing modes.
"""

import os
from typing import TYPE_CHECKING

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.processor.parallel import process_in_parallel
from system.algo_trader.backtest.processor.sequential import process_sequentially
from system.algo_trader.backtest.results.hash import compute_backtest_hash

if TYPE_CHECKING:
    from system.algo_trader.strategy.filters.core import FilterPipeline
    from system.algo_trader.strategy.strategy import Strategy


def get_backtest_database() -> str:
    """Get the appropriate database for backtest results based on environment.

    Returns:
        'backtest' for prod environment, 'backtest-dev' otherwise.
    """
    env = os.getenv("INFLUXDB3_ENVIRONMENT", "").lower()
    return "backtest" if env == "prod" else "backtest-dev"


class BacktestProcessor:
    """Orchestrates backtest execution for multiple tickers.

    This class manages the execution of backtests across multiple tickers,
    supporting both multiprocessing and sequential execution modes.

    Args:
        logger: Optional logger instance. If not provided, creates a new logger.
    """

    def __init__(self, logger=None) -> None:
        """Initialize BacktestProcessor.

        Args:
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def _build_worker_args(
        self,
        tickers: list[str],
        strategy_type: str,
        strategy_params: dict,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        step_frequency: str,
        database: str,
        results_database: str,
        execution_config: ExecutionConfig,
        capital_per_trade: float,
        risk_free_rate: float,
        backtest_id: str,
        walk_forward: bool,
        train_days: int | None,
        test_days: int | None,
        train_split: float | None,
        initial_account_value: float | None = None,
        trade_percentage: float | None = None,
        filter_pipeline: "FilterPipeline | None" = None,
        position_manager_config_dict: dict | None = None,
        filter_config_dict: dict | None = None,
        hash_id: str | None = None,
    ) -> list[tuple]:
        """Build worker arguments for each ticker.

        Creates a list of argument tuples, one per ticker, for multiprocessing workers.

        Args:
            tickers: List of ticker symbols to process.
            strategy_type: Type of strategy to use.
            strategy_params: Dictionary of strategy parameters.
            start_date: Start date for backtest.
            end_date: End date for backtest.
            step_frequency: Frequency for time steps.
            database: Database name for data access.
            results_database: Database name for results storage.
            execution_config: Execution configuration with slippage and commission.
            capital_per_trade: Capital allocated per trade.
            risk_free_rate: Risk-free rate for Sharpe ratio calculation.
            backtest_id: Unique identifier for this backtest run.
            walk_forward: Whether to use walk-forward analysis.
            train_days: Number of training days for walk-forward.
            test_days: Number of test days for walk-forward.
            train_split: Training split ratio for walk-forward.
            initial_account_value: Optional initial account value for account tracking.
            trade_percentage: Optional percentage of account to use per trade.
            filter_pipeline: Optional FilterPipeline instance for filtering signals.
            position_manager_config_dict: Optional dictionary containing position
                manager configuration. If None, position manager is not used.
            filter_config_dict: Optional dictionary containing filter configuration
                for hash computation. If None, filters are not included in hash.

        Returns:
            List of tuples, each containing arguments for a worker process.
        """
        execution_config_dict = {
            "slippage_bps": execution_config.slippage_bps,
            "commission_per_share": execution_config.commission_per_share,
        }

        return [
            (
                ticker,
                strategy_type,
                strategy_params,
                start_date,
                end_date,
                step_frequency,
                database,
                results_database,
                execution_config_dict,
                capital_per_trade,
                risk_free_rate,
                backtest_id,
                walk_forward,
                train_days,
                test_days,
                train_split,
                initial_account_value,
                trade_percentage,
                filter_pipeline,
                position_manager_config_dict,
                filter_config_dict,
                hash_id,
            )
            for ticker in tickers
        ]

    def _print_summary(self, summary: dict[str, int | str]) -> None:
        """Print backtest processing summary to console.

        Args:
            summary: Dictionary containing processing statistics.
        """
        print(f"\n{'=' * 50}")
        print("Backtest Processing Summary")
        print(f"{'=' * 50}")
        if "hash_id" in summary:
            print(f"Hash ID: {summary['hash_id']}")
        if "backtest_id" in summary:
            print(f"Backtest ID: {summary['backtest_id']}")
        print(f"Total Tickers: {summary['total']}")
        print(f"Successfully Processed: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"{'=' * 50}\n")

    def process_tickers(
        self,
        strategy: "Strategy",
        tickers: list[str],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        step_frequency: str,
        database: str,
        results_database: str,
        execution_config: ExecutionConfig,
        capital_per_trade: float,
        risk_free_rate: float,
        strategy_params: dict,
        backtest_id: str,
        walk_forward: bool = False,
        train_days: int | None = None,
        test_days: int | None = None,
        train_split: float | None = None,
        max_processes: int | None = None,
        use_multiprocessing: bool = True,
        initial_account_value: float | None = None,
        trade_percentage: float | None = None,
        filter_pipeline: "FilterPipeline | None" = None,
        position_manager_config_dict: dict | None = None,
        filter_config_dict: dict | None = None,
    ) -> None:
        """Process multiple tickers through backtest execution.

        Executes backtests for all specified tickers, either in parallel using
        multiprocessing or sequentially. Results are written to Redis queues
        for later publication to InfluxDB.

        Args:
            strategy: Strategy instance to use for backtesting.
            tickers: List of ticker symbols to process.
            start_date: Start date for backtest period.
            end_date: End date for backtest period.
            step_frequency: Frequency for time steps ('daily', 'hourly', etc.).
            database: Database name for data access.
            results_database: Database name for results storage.
            execution_config: Execution configuration with slippage and commission.
            capital_per_trade: Capital allocated per trade.
            risk_free_rate: Risk-free rate for Sharpe ratio calculation.
            strategy_params: Dictionary of strategy parameters.
            backtest_id: Unique identifier for this backtest run.
            walk_forward: Whether to use walk-forward analysis.
            train_days: Number of training days for walk-forward.
            test_days: Number of test days for walk-forward.
            train_split: Training split ratio for walk-forward.
            max_processes: Maximum number of parallel processes.
                If None, uses CPU count - 2.
            use_multiprocessing: Whether to use parallel processing.
                If False, processes sequentially.
            initial_account_value: Optional initial account value for account tracking.
            trade_percentage: Optional percentage of account to use per trade.
            filter_pipeline: Optional FilterPipeline instance for filtering signals.
            position_manager_config_dict: Optional dictionary containing position
                manager configuration. If None, position manager is not used.
            filter_config_dict: Optional dictionary containing filter configuration.
                If None, filters are not used.
        """
        if not tickers:
            self.logger.error("No tickers provided")
            return

        self.logger.info(
            f"Processing backtest for {len(tickers)} tickers with "
            f"strategy={strategy.strategy_name}, "
            f"date_range={start_date.date()} to {end_date.date()}, "
            f"backtest_id={backtest_id}"
        )

        strategy_type = type(strategy).__name__

        hash_id = compute_backtest_hash(
            strategy_params=strategy_params,
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency=step_frequency,
            database=database,
            tickers=tickers,
            capital_per_trade=capital_per_trade,
            risk_free_rate=risk_free_rate,
            walk_forward=walk_forward,
            train_days=train_days,
            test_days=test_days,
            train_split=train_split,
            position_manager_params=position_manager_config_dict,
            filter_params=filter_config_dict,
        )

        worker_args = self._build_worker_args(
            tickers=tickers,
            strategy_type=strategy_type,
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            step_frequency=step_frequency,
            database=database,
            results_database=results_database,
            execution_config=execution_config,
            capital_per_trade=capital_per_trade,
            risk_free_rate=risk_free_rate,
            backtest_id=backtest_id,
            walk_forward=walk_forward,
            train_days=train_days,
            test_days=test_days,
            train_split=train_split,
            initial_account_value=initial_account_value,
            trade_percentage=trade_percentage,
            filter_pipeline=filter_pipeline,
            position_manager_config_dict=position_manager_config_dict,
            filter_config_dict=filter_config_dict,
            hash_id=hash_id,
        )

        if use_multiprocessing:
            summary = process_in_parallel(
                worker_args,
                tickers,
                max_processes,
                self.logger,
                hash_id=hash_id,
                backtest_id=backtest_id,
            )
        else:
            summary = process_sequentially(
                worker_args, tickers, self.logger, hash_id=hash_id, backtest_id=backtest_id
            )

        self._print_summary(summary)
