import multiprocessing
from typing import TYPE_CHECKING
from uuid import uuid4

import pandas as pd

from infrastructure.config import ProcessConfig
from infrastructure.logging.logger import get_logger
from infrastructure.multiprocess.process_manager import ProcessManager
from system.algo_trader.backtest.engine import BacktestEngine
from system.algo_trader.backtest.execution import ExecutionConfig
from system.algo_trader.backtest.results import ResultsWriter
from system.algo_trader.backtest.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_TRADES_QUEUE_NAME,
)

if TYPE_CHECKING:
    from system.algo_trader.strategy.base import BaseStrategy


def _backtest_ticker_worker(args: tuple) -> dict:
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

    from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy

    engine = None
    strategy_instance = None
    try:
        logger = get_logger("BacktestWorker")
        logger.debug(f"Starting backtest for {ticker}")

        if strategy_type == "SMACrossoverStrategy":
            strategy_instance = SMACrossoverStrategy(
                short_window=strategy_params_local["short_window"],
                long_window=strategy_params_local["long_window"],
                database=database_local,
                use_threading=False,
            )
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

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

        worker_results_writer = ResultsWriter()
        trades_success = worker_results_writer.write_trades(
            trades=results.trades,
            strategy_name=results.strategy_name,
            ticker=ticker,
            backtest_id=backtest_id_local,
            strategy_params=strategy_params_local,
            execution_config=execution_config,
            start_date=start_date_local,
            end_date=end_date_local,
            step_frequency=step_frequency_local,
            database=database_local,
            tickers=[ticker],
            capital_per_trade=capital_per_trade_local,
            risk_free_rate=risk_free_rate_local,
            walk_forward=walk_forward_local,
            train_days=train_days_local,
            test_days=test_days_local,
            train_split=train_split_local,
        )

        metrics_success = False
        if results.metrics and trades_success:
            metrics_success = worker_results_writer.write_metrics(
                metrics=results.metrics,
                strategy_name=results.strategy_name,
                ticker=ticker,
                backtest_id=backtest_id_local,
                strategy_params=strategy_params_local,
                execution_config=execution_config,
                start_date=start_date_local,
                end_date=end_date_local,
                step_frequency=step_frequency_local,
                database=database_local,
                tickers=[ticker],
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
        logger = get_logger("BacktestWorker")
        logger.error(f"{ticker}: Exception during backtest: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if engine is not None:
            try:
                engine.influx_client.close()
            except Exception as e:
                logger = get_logger("BacktestWorker")
                logger.warning(f"{ticker}: Error closing InfluxDB client: {e}")
        if strategy_instance is not None:
            try:
                strategy_instance.close()
            except Exception:
                pass


class BacktestProcessor:
    def __init__(self, logger=None):
        self.logger = logger or get_logger(self.__class__.__name__)

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
        if not tickers:
            self.logger.error("No tickers provided")
            return

        self.logger.info(
            f"Processing backtest for {len(tickers)} tickers with "
            f"strategy={strategy.strategy_name}, date_range={start_date.date()} to {end_date.date()}"
        )

        backtest_id = str(uuid4())
        self.logger.info(f"Backtest ID: {backtest_id}")

        strategy_type = type(strategy).__name__

        if not use_multiprocessing:
            self.logger.info("Processing tickers sequentially (multiprocessing disabled)...")
            successful = 0
            failed = 0

            for ticker in tickers:
                execution_config_dict = {
                    "slippage_bps": execution_config.slippage_bps,
                    "commission_per_share": execution_config.commission_per_share,
                }
                args = (
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
                result = _backtest_ticker_worker(args)
                if result.get("success", False):
                    successful += 1
                else:
                    failed += 1

            summary = {"successful": successful, "failed": failed, "total": len(tickers)}
        else:
            process_config = ProcessConfig(max_processes=max_processes)
            process_manager = ProcessManager(config=process_config)

            execution_config_dict = {
                "slippage_bps": execution_config.slippage_bps,
                "commission_per_share": execution_config.commission_per_share,
            }

            worker_args = [
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

            max_processes = process_config.max_processes or max(1, multiprocessing.cpu_count() - 2)
            if len(tickers) > max_processes:
                self.logger.info(
                    f"Starting multiprocessing with {len(tickers)} tickers using {max_processes} processes "
                    f"(batching: {len(tickers)} tickers will be processed in batches of {max_processes})"
                )
            else:
                self.logger.info(
                    f"Starting multiprocessing with {len(tickers)} tickers using {max_processes} processes"
                )
            results_list = process_manager.map(_backtest_ticker_worker, worker_args)

            successful = sum(1 for r in results_list if r.get("success", False))
            failed = len(results_list) - successful

            summary = {"successful": successful, "failed": failed, "total": len(tickers)}

            process_manager.close_pool()

        print(f"\n{'=' * 50}")
        print("Backtest Processing Summary")
        print(f"{'=' * 50}")
        print(f"Total Tickers: {len(tickers)}")
        print(f"Successfully Processed: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Trades Queue: {BACKTEST_TRADES_QUEUE_NAME}")
        print(f"Metrics Queue: {BACKTEST_METRICS_QUEUE_NAME}")
        print("Redis TTL: 3600s")
        print("\nResults will be published to InfluxDB by the influx-publisher service.")
        print(f"{'=' * 50}\n")
