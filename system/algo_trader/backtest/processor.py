import time
from typing import TYPE_CHECKING
from uuid import uuid4

import pandas as pd

from infrastructure.config import ThreadConfig
from infrastructure.logging.logger import get_logger
from infrastructure.threads.thread_manager import ThreadManager
from system.algo_trader.backtest.engine import BacktestEngine, BacktestResults
from system.algo_trader.backtest.execution import ExecutionConfig
from system.algo_trader.backtest.results import ResultsWriter
from system.algo_trader.backtest.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_TRADES_QUEUE_NAME,
)

if TYPE_CHECKING:
    from system.algo_trader.strategy.base import BaseStrategy

MAX_THREADS = 4


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
        max_threads: int = MAX_THREADS,
        use_threading: bool = True,
    ) -> None:
        if not tickers:
            self.logger.error("No tickers provided")
            return

        self.logger.info(
            f"Processing backtest for {len(tickers)} tickers with "
            f"strategy={strategy.strategy_name}, date_range={start_date.date()} to {end_date.date()}"
        )

        results_writer = ResultsWriter()
        backtest_id = str(uuid4())
        self.logger.info(f"Backtest ID: {backtest_id}")

        def backtest_ticker(ticker: str) -> dict:
            engine = None
            try:
                self.logger.info(f"Starting backtest for {ticker}")
                engine = BacktestEngine(
                    strategy=strategy,
                    tickers=[ticker],
                    start_date=start_date,
                    end_date=end_date,
                    step_frequency=step_frequency,
                    database=database,
                    execution_config=execution_config,
                    capital_per_trade=capital_per_trade,
                    risk_free_rate=risk_free_rate,
                )

                results = engine.run_ticker(ticker)

                if results.trades.empty:
                    self.logger.info(f"{ticker}: No trades generated")
                    return {"success": True, "trades": 0}

                # Print detailed summary for this ticker
                if results.metrics:
                    self.logger.info(
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

                trades_success = results_writer.write_trades(
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
                    metrics_success = results_writer.write_metrics(
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

                if trades_success and metrics_success:
                    self.logger.debug(
                        f"{ticker}: Successfully enqueued {len(results.trades)} trades and metrics to Redis"
                    )
                    return {"success": True, "trades": len(results.trades)}
                else:
                    self.logger.error(f"{ticker}: Failed to enqueue results to Redis")
                    return {"success": False, "error": "Redis enqueue failed"}

            except Exception as e:
                self.logger.error(f"{ticker}: Exception during backtest: {e}", exc_info=True)
                return {"success": False, "error": str(e)}
            finally:
                if engine is not None:
                    try:
                        engine.influx_client.close()
                    except Exception as e:
                        self.logger.warning(f"{ticker}: Error closing InfluxDB client: {e}")

        if not use_threading:
            self.logger.info("Processing tickers sequentially (threading disabled)...")
            successful = 0
            failed = 0

            for ticker in tickers:
                result = backtest_ticker(ticker)
                if result.get("success", False):
                    successful += 1
                else:
                    failed += 1

            summary = {"successful": successful, "failed": failed, "total": len(tickers)}
        else:
            thread_config = ThreadConfig(max_threads=max_threads)
            thread_manager = ThreadManager(config=thread_config)

            if len(tickers) > max_threads:
                self.logger.info(
                    f"Ticker count ({len(tickers)}) exceeds max_threads ({max_threads}). "
                    f"Batching will be used."
                )

            remaining_tickers = list(tickers)
            last_log_time = time.time()

            self.logger.info("Starting batch processing...")

            while remaining_tickers:
                active_count = thread_manager.get_active_thread_count()
                available_slots = max_threads - active_count

                if available_slots > 0 and remaining_tickers:
                    batch_size = min(available_slots, len(remaining_tickers))
                    batch = remaining_tickers[:batch_size]
                    remaining_tickers = remaining_tickers[batch_size:]

                    for ticker in batch:
                        try:
                            thread_manager.start_thread(
                                target=backtest_ticker,
                                name=f"backtest-{ticker}",
                                args=(ticker,),
                            )
                            self.logger.debug(f"Started thread for {ticker}")
                        except RuntimeError as e:
                            self.logger.error(f"Failed to start thread for {ticker}: {e}")
                            remaining_tickers.append(ticker)

                time.sleep(0.5)

                current_time = time.time()
                if current_time - last_log_time >= 10:
                    with thread_manager.lock:
                        completed_count = sum(
                            1
                            for status in thread_manager.threads.values()
                            if not status.thread.is_alive() and status.status in ("stopped", "error")
                        )
                    started_count = len(tickers) - len(remaining_tickers)
                    self.logger.info(
                        f"Progress: {started_count} started, {completed_count} completed, "
                        f"{len(remaining_tickers)} remaining, {active_count} active threads"
                    )
                    last_log_time = current_time

            self.logger.info("Waiting for all threads to complete...")
            thread_manager.wait_for_all_threads(timeout=600)

            summary = thread_manager.get_results_summary()
            self.logger.info(
                f"Batch processing complete: {summary['successful']} successful, "
                f"{summary['failed']} failed out of {len(tickers)} total tickers"
            )

            thread_manager.cleanup_dead_threads()

        print(f"\n{'=' * 50}")
        print("Backtest Processing Summary")
        print(f"{'=' * 50}")
        print(f"Total Tickers: {len(tickers)}")
        print(f"Successfully Processed: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Trades Queue: {BACKTEST_TRADES_QUEUE_NAME}")
        print(f"Metrics Queue: {BACKTEST_METRICS_QUEUE_NAME}")
        print(f"Redis TTL: 3600s")
        print("\nResults will be published to InfluxDB by the influx-publisher service.")
        print(f"{'=' * 50}\n")

