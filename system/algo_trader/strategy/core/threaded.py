"""Threaded execution for trading strategies.

This module provides functionality to execute trading strategies in parallel
using threads, improving performance when processing multiple tickers.
"""

import time

import pandas as pd

from infrastructure.logging.logger import get_logger
from infrastructure.threads.thread_manager import ThreadManager
from system.algo_trader.strategy.core.sequential import log_multi_summary


def run_threaded(
    strategy,
    tickers: list[str],
    start_time: str | None,
    end_time: str | None,
    limit: int | None,
    write_signals: bool,
    thread_manager: ThreadManager,
    logger=None,
) -> pd.DataFrame:
    """Execute strategy in parallel using threads for multiple tickers.

    Runs strategy for each ticker in parallel threads, managing thread pool
    and collecting signal summaries. Uses batching when ticker count exceeds
    max_threads.

    Args:
        strategy: Strategy instance to execute.
        tickers: List of ticker symbols to process.
        start_time: Optional start time for data query.
        end_time: Optional end time for data query.
        limit: Optional limit on number of data points.
        write_signals: Whether to write signals to InfluxDB.
        thread_manager: ThreadManager instance for thread pool management.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        Combined DataFrame containing signals from all tickers.
    """
    logger = logger or get_logger("ThreadedStrategy")

    def process_ticker(ticker: str) -> dict:
        try:
            summary = strategy.run_strategy(ticker, start_time, end_time, limit, write_signals)
            return {"success": True, "summary": summary}
        except Exception as e:
            logger.error(f"Thread failed for {ticker}: {e}")
            return {"success": False, "error": str(e)}

    max_threads = thread_manager.config.max_threads
    logger.info(f"ThreadManager initialized with max_threads={max_threads}")

    if len(tickers) > max_threads:
        logger.info(
            f"Ticker count ({len(tickers)}) exceeds max_threads ({max_threads}). "
            f"Batching will be used. Consider increasing THREAD_MAX_THREADS "
            f"for faster processing."
        )

    remaining_tickers = list(tickers)
    last_log_time = time.time()

    logger.info("Starting batch processing...")

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
                        target=process_ticker,
                        name=f"strategy-{ticker}",
                        args=(ticker,),
                    )
                    logger.debug(f"Started thread for {ticker}")
                except RuntimeError as e:
                    logger.error(f"Failed to start thread for {ticker}: {e}")
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
            logger.info(
                f"Progress: {started_count} started, {completed_count} completed, "
                f"{len(remaining_tickers)} remaining, {active_count} active threads"
            )
            last_log_time = current_time

    logger.info("Waiting for all strategy threads to complete...")
    thread_manager.wait_for_all_threads(timeout=300)

    all_results = thread_manager.get_all_results()
    all_summaries = []

    for result in all_results.values():
        if result and result.get("success"):
            summary = result.get("summary")
            if summary is not None and not summary.empty:
                all_summaries.append(summary)

    thread_manager.cleanup_dead_threads()

    if write_signals:
        strategy.influx_client.wait_for_batches(timeout=30)

    if not all_summaries:
        logger.info("No signals generated for any tickers")
        return pd.DataFrame()

    combined = pd.concat(all_summaries, ignore_index=True)
    log_multi_summary(combined, logger)
    return combined
