"""Backtest processor for parallel ticker processing.

This module provides functionality for processing multiple tickers in parallel
using multiprocessing.
"""

import multiprocessing
from typing import TYPE_CHECKING
from uuid import uuid4

import pandas as pd

from infrastructure.config import ProcessConfig
from infrastructure.logging.logger import get_logger
from infrastructure.multiprocess.process_manager import ProcessManager
from system.algo_trader.backtest.engine import BacktestEngine, BacktestResults
from system.algo_trader.backtest.execution import ExecutionConfig
from system.algo_trader.backtest.results import ResultsWriter
from system.algo_trader.backtest.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_TRADES_QUEUE_NAME,
)

if TYPE_CHECKING:
    from system.algo_trader.strategy.base import BaseStrategy

# Import strategy classes at module level to avoid import in worker function
from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy


def _create_strategy_instance(
    strategy_type: str, strategy_params: dict, database: str
) -> "BaseStrategy":
    """Create strategy instance from type and parameters.

    Args:
        strategy_type: Type name of strategy class.
        strategy_params: Dictionary of strategy parameters.
        database: Database name for strategy.

    Returns:
        Strategy instance.

    Raises:
        ValueError: If strategy type is unknown.
    """
    if strategy_type == "SMACrossoverStrategy":
        return SMACrossoverStrategy(
            short_window=strategy_params["short_window"],
            long_window=strategy_params["long_window"],
            database=database,
            use_threading=False,
        )
    raise ValueError(f"Unknown strategy type: {strategy_type}")


def _log_backtest_results(ticker: str, results: "BacktestResults") -> None:
    """Log backtest results for a ticker.

    Args:
        ticker: Ticker symbol.
        results: BacktestResults object.
    """
    logger = get_logger("BacktestWorker")
    if results.metrics:
        logger.info(
            f"\n{ticker} Backtest Results:\n"
            f"  Strategy: {results.strategy_name}\n"
            f"  Total Trades: {results.metrics.get('total_trades', 0)}\n"
            f"  Total Profit: ${results.metrics.get('total_profit', 0):,.2f} "
            f"({results.metrics.get('total_profit_pct', 0):.2f}%)\n"
            f"  Max Drawdown: {results.metrics.get('max_drawdown', 0):.2f}%\n"
            f"  Sharpe Ratio: {results.metrics.get('sharpe_ratio', 0):.4f}\n"
            f"  Win Rate: {results.metrics.get('win_rate', 0):.2f}%\n"
            f"  Efficiency: {results.metrics.get('avg_efficiency', 0):.2f}%\n"
        )


def _write_backtest_results(
    results: "BacktestResults",
    ticker: str,
    backtest_id: str,
    strategy_params: dict,
    execution_config: ExecutionConfig,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    step_frequency: str,
    database: str,
    capital_per_trade: float,
    risk_free_rate: float,
    walk_forward: bool,
    train_days: int | None,
    test_days: int | None,
    train_split: float | None,
) -> tuple[bool, bool]:
    """Write backtest results to Redis queues.

    Args:
        results: BacktestResults object.
        ticker: Ticker symbol.
        backtest_id: Backtest identifier.
        strategy_params: Strategy parameters.
        execution_config: Execution configuration.
        start_date: Start date.
        end_date: End date.
        step_frequency: Step frequency.
        database: Database name.
        capital_per_trade: Capital per trade.
        risk_free_rate: Risk-free rate.
        walk_forward: Walk-forward flag.
        train_days: Training days.
        test_days: Testing days.
        train_split: Train/test split.

    Returns:
        Tuple of (trades_success, metrics_success).
    """
    writer = ResultsWriter()
    trades_success = writer.write_trades(
        trades=results.trades,
        strategy_name=results.strategy_name,
        ticker=ticker,
        backtest_id=backtest_id,
        strategy_params=strategy_params,
        execution_config=execution_config,
        start_date=start_date,
        end_date=end_date,
        step_frequency=step_frequency,
        database=database,
        tickers=[ticker],
        capital_per_trade=capital_per_trade,
        risk_free_rate=risk_free_rate,
        walk_forward=walk_forward,
        train_days=train_days,
        test_days=test_days,
        train_split=train_split,
    )

    metrics_success = False
    if results.metrics and trades_success:
        metrics_success = writer.write_metrics(
            metrics=results.metrics,
            strategy_name=results.strategy_name,
            ticker=ticker,
            backtest_id=backtest_id,
            strategy_params=strategy_params,
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency=step_frequency,
            database=database,
            tickers=[ticker],
            capital_per_trade=capital_per_trade,
            risk_free_rate=risk_free_rate,
            walk_forward=walk_forward,
            train_days=train_days,
            test_days=test_days,
            train_split=train_split,
        )

    return trades_success, metrics_success


def _backtest_ticker_worker(args: tuple) -> dict:
    """Worker function for processing a single ticker in a separate process.

    Args:
        args: Tuple containing ticker and backtest configuration.

    Returns:
        Dictionary containing backtest results for the ticker.
    """
    (
        ticker,
        strategy_type,
        strategy_params_local,
        start_date_local,
        end_date_local,
        step_frequency_local,
        database_local,
        execution_config_dict,
        capital_per_trade_local,
        risk_free_rate_local,
        backtest_id_local,
        walk_forward_local,
        train_days_local,
        test_days_local,
        train_split_local,
    ) = args

    engine = None
    strategy_instance = None
    logger = get_logger("BacktestWorker")

    try:
        logger.debug(f"Starting backtest for {ticker}")

        strategy_instance = _create_strategy_instance(
            strategy_type, strategy_params_local, database_local
        )

        execution_config = ExecutionConfig(
            slippage_bps=execution_config_dict["slippage_bps"],
            commission_per_share=execution_config_dict["commission_per_share"],
        )

        engine = BacktestEngine(
            strategy=strategy_instance,
            tickers=[ticker],
            start_date=start_date_local,
            end_date=end_date_local,
            step_frequency=step_frequency_local,
            database=database_local,
            execution_config=execution_config,
            capital_per_trade=capital_per_trade_local,
            risk_free_rate=risk_free_rate_local,
        )

        results = engine.run_ticker(ticker)

        if results.trades.empty:
            logger.debug(f"{ticker}: No trades generated")
            return {"success": True, "trades": 0}

        _log_backtest_results(ticker, results)

        trades_success, metrics_success = _write_backtest_results(
            results=results,
            ticker=ticker,
            backtest_id=backtest_id_local,
            strategy_params=strategy_params_local,
            execution_config=execution_config,
            start_date=start_date_local,
            end_date=end_date_local,
            step_frequency=step_frequency_local,
            database=database_local,
            capital_per_trade=capital_per_trade_local,
            risk_free_rate=risk_free_rate_local,
            walk_forward=walk_forward_local,
            train_days=train_days_local,
            test_days=test_days_local,
            train_split=train_split_local,
        )

        if trades_success and metrics_success:
            logger.debug(
                f"{ticker}: Successfully enqueued {len(results.trades)} trades and metrics to Redis"
            )
            return {"success": True, "trades": len(results.trades)}
        else:
            logger.error(f"{ticker}: Failed to enqueue results to Redis")
            return {"success": False, "error": "Redis enqueue failed"}

    except Exception as e:
        logger.error(f"{ticker}: Exception during backtest: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if engine is not None:
            try:
                engine.influx_client.close()
            except Exception as e:
                logger.warning(f"{ticker}: Error closing InfluxDB client: {e}")
        if strategy_instance is not None:
            try:
                strategy_instance.close()
            except Exception:
                pass


class BacktestProcessor:
    """Processor for running backtests on multiple tickers.

    Supports both sequential and parallel processing using multiprocessing.

    Args:
        logger: Optional logger instance. If not provided, creates a new one.
    """

    def __init__(self, logger=None) -> None:
        """Initialize backtest processor.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.
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
        execution_config: ExecutionConfig,
        capital_per_trade: float,
        risk_free_rate: float,
        backtest_id: str,
        walk_forward: bool,
        train_days: int | None,
        test_days: int | None,
        train_split: float | None,
    ) -> list[tuple]:
        """Build worker arguments for each ticker.

        Args:
            tickers: List of ticker symbols.
            strategy_type: Strategy type name.
            strategy_params: Strategy parameters.
            start_date: Start date.
            end_date: End date.
            step_frequency: Step frequency.
            database: Database name.
            execution_config: Execution configuration.
            capital_per_trade: Capital per trade.
            risk_free_rate: Risk-free rate.
            backtest_id: Backtest identifier.
            walk_forward: Walk-forward flag.
            train_days: Training days.
            test_days: Testing days.
            train_split: Train/test split.

        Returns:
            List of argument tuples for worker function.
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
                execution_config_dict,
                capital_per_trade,
                risk_free_rate,
                backtest_id,
                walk_forward,
                train_days,
                test_days,
                train_split,
            )
            for ticker in tickers
        ]

    def _process_sequentially(self, worker_args: list[tuple], tickers: list[str]) -> dict[str, int]:
        """Process tickers sequentially.

        Args:
            worker_args: List of argument tuples for worker function.
            tickers: List of ticker symbols.

        Returns:
            Summary dictionary with successful/failed counts.
        """
        self.logger.info("Processing tickers sequentially (multiprocessing disabled)...")
        successful = 0
        failed = 0

        for args in worker_args:
            result = _backtest_ticker_worker(args)
            if result.get("success", False):
                successful += 1
            else:
                failed += 1

        return {"successful": successful, "failed": failed, "total": len(tickers)}

    def _process_in_parallel(
        self, worker_args: list[tuple], tickers: list[str], max_processes: int | None
    ) -> dict[str, int]:
        """Process tickers in parallel using multiprocessing.

        Args:
            worker_args: List of argument tuples for worker function.
            tickers: List of ticker symbols.
            max_processes: Maximum number of processes.

        Returns:
            Summary dictionary with successful/failed counts.
        """
        process_config = ProcessConfig(max_processes=max_processes)
        process_manager = ProcessManager(config=process_config)

        max_processes = process_config.max_processes or max(1, multiprocessing.cpu_count() - 2)
        if len(tickers) > max_processes:
            self.logger.info(
                f"Starting multiprocessing with {len(tickers)} tickers "
                f"using {max_processes} processes "
                f"(batching: {len(tickers)} tickers will be processed "
                f"in batches of {max_processes})"
            )
        else:
            self.logger.info(
                f"Starting multiprocessing with {len(tickers)} tickers "
                f"using {max_processes} processes"
            )

        results_list = process_manager.map(_backtest_ticker_worker, worker_args)
        process_manager.close_pool()

        successful = sum(1 for r in results_list if r.get("success", False))
        failed = len(results_list) - successful

        return {"successful": successful, "failed": failed, "total": len(tickers)}

    def _print_summary(self, summary: dict[str, int]) -> None:
        """Print backtest processing summary.

        Args:
            summary: Summary dictionary with counts.
        """
        print(f"\n{'=' * 50}")
        print("Backtest Processing Summary")
        print(f"{'=' * 50}")
        print(f"Total Tickers: {summary['total']}")
        print(f"Successfully Processed: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Trades Queue: {BACKTEST_TRADES_QUEUE_NAME}")
        print(f"Metrics Queue: {BACKTEST_METRICS_QUEUE_NAME}")
        print("Redis TTL: 3600s")
        print("\nResults will be published to InfluxDB by the influx-publisher service.")
        print(f"{'=' * 50}\n")

    def process_tickers(
        self,
        strategy: "BaseStrategy",
        tickers: list[str],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        step_frequency: str,
        database: str,
        execution_config: ExecutionConfig,
        capital_per_trade: float,
        risk_free_rate: float,
        strategy_params: dict,
        walk_forward: bool = False,
        train_days: int | None = None,
        test_days: int | None = None,
        train_split: float | None = None,
        max_processes: int | None = None,
        use_multiprocessing: bool = True,
    ) -> None:
        """Process multiple tickers through backtesting.

        Args:
            strategy: Strategy instance to backtest.
            tickers: List of ticker symbols.
            start_date: Start date for backtest.
            end_date: End date for backtest.
            step_frequency: Time-stepping frequency.
            database: InfluxDB database name.
            execution_config: Execution simulation configuration.
            capital_per_trade: Capital per trade.
            risk_free_rate: Risk-free rate for metrics.
            strategy_params: Strategy parameters dictionary.
            walk_forward: Enable walk-forward analysis.
            train_days: Training period days for walk-forward.
            test_days: Testing period days for walk-forward.
            train_split: Train/test split ratio.
            max_processes: Maximum number of processes.
            use_multiprocessing: Whether to use multiprocessing.
        """
        if not tickers:
            self.logger.error("No tickers provided")
            return

        self.logger.info(
            f"Processing backtest for {len(tickers)} tickers with "
            f"strategy={strategy.strategy_name}, "
            f"date_range={start_date.date()} to {end_date.date()}"
        )

        backtest_id = str(uuid4())
        self.logger.info(f"Backtest ID: {backtest_id}")

        strategy_type = type(strategy).__name__

        worker_args = self._build_worker_args(
            tickers=tickers,
            strategy_type=strategy_type,
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            step_frequency=step_frequency,
            database=database,
            execution_config=execution_config,
            capital_per_trade=capital_per_trade,
            risk_free_rate=risk_free_rate,
            backtest_id=backtest_id,
            walk_forward=walk_forward,
            train_days=train_days,
            test_days=test_days,
            train_split=train_split,
        )

        if use_multiprocessing:
            summary = self._process_in_parallel(worker_args, tickers, max_processes)
        else:
            summary = self._process_sequentially(worker_args, tickers)

        self._print_summary(summary)
