"""Fundamentals data processor.

This module provides processing logic for fetching and storing company
fundamentals data from SEC company facts API.
"""

import time

from infrastructure.config import ThreadConfig
from infrastructure.logging.logger import get_logger
from infrastructure.threads.thread_manager import ThreadManager
from system.algo_trader.datasource.populate.fundamentals.utils import (
    FUNDAMENTALS_QUEUE_NAME,
    FUNDAMENTALS_REDIS_TTL,
    FUNDAMENTALS_STATIC_QUEUE_NAME,
    dataframe_to_dict,
    print_summary,
)
from system.algo_trader.datasource.sec.tickers.main import Tickers
from system.algo_trader.redis.queue_broker import QueueBroker


class FundamentalsProcessor:
    """Processor for fundamentals data fetching and storage.

    Handles concurrent fetching of company facts data and publishing to
    Redis queues for downstream processing.
    """

    def __init__(self, logger=None):
        """Initialize fundamentals processor.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def process_tickers(  # noqa: C901, PLR0915
        self,
        tickers: list[str],
        lookback_period: int,
        write: bool,
        max_threads: int,
    ) -> None:
        """Process tickers to fetch and store fundamentals data.

        Args:
            tickers: List of ticker symbols to process.
            lookback_period: Number of years to look back for data.
            write: If True, write data to Redis queues. If False, dry-run mode.
            max_threads: Maximum number of concurrent threads for processing.
        """
        if tickers is None:
            self.logger.error("No tickers found")
            return

        self.logger.info(
            f"Executing fundamentals data population for {len(tickers)} tickers with "
            f"lookback period: {lookback_period} years, write: {write}, max_threads: {max_threads}"
        )

        tickers_source = Tickers()
        queue_broker = None

        if write:
            queue_broker = QueueBroker(namespace="queue")
            self.logger.info(
                f"QueueBroker initialized for queues: {FUNDAMENTALS_QUEUE_NAME}, "
                f"{FUNDAMENTALS_STATIC_QUEUE_NAME}"
            )

        thread_config = ThreadConfig(max_threads=max_threads)
        thread_manager = ThreadManager(config=thread_config)
        self.logger.info(f"ThreadManager initialized with max_threads={max_threads}")

        if len(tickers) > max_threads:
            self.logger.info(
                f"Ticker count ({len(tickers)}) exceeds max_threads ({max_threads}). "
                f"Batching will be used."
            )

        summary_stats = {
            "total": len(tickers),
            "successful": 0,
            "failed": 0,
            "static_rows": 0,
            "time_series_rows": 0,
            "market_cap_rows": 0,
        }

        def fetch_ticker_fundamentals(ticker: str) -> dict:  # noqa: PLR0911
            try:
                self.logger.debug(f"Fetching company facts for {ticker}")

                company_facts = tickers_source.get_company_facts(ticker, years_back=lookback_period)
                if not company_facts:
                    self.logger.error(f"{ticker}: Failed to retrieve company facts")
                    return {"success": False, "error": "Failed to retrieve company facts"}

                static_data = company_facts.get("static")
                time_series_df = company_facts.get("time_series")

                if static_data is None or time_series_df is None:
                    self.logger.error(f"{ticker}: Missing static or time_series data")
                    return {"success": False, "error": "Missing data"}

                if time_series_df.empty:
                    self.logger.warning(f"{ticker}: Time series DataFrame is empty")
                    return {"success": False, "error": "Empty time series"}

                market_cap_count = (
                    time_series_df["market_cap"].notna().sum()
                    if "market_cap" in time_series_df.columns
                    else 0
                )
                summary_stats["market_cap_rows"] += market_cap_count

                if write:
                    if queue_broker:
                        static_enqueue_success = queue_broker.enqueue(
                            queue_name=FUNDAMENTALS_STATIC_QUEUE_NAME,
                            item_id=ticker,
                            data=static_data,
                            ttl=FUNDAMENTALS_REDIS_TTL,
                        )

                        if static_enqueue_success:
                            summary_stats["static_rows"] += 1
                            self.logger.debug(
                                f"{ticker}: Successfully enqueued static data to Redis"
                            )
                        else:
                            self.logger.error(f"{ticker}: Failed to enqueue static data to Redis")
                            return {"success": False, "error": "Redis static enqueue failed"}

                        time_series_dict = dataframe_to_dict(time_series_df)
                        queue_data = {
                            "ticker": ticker,
                            "data": time_series_dict,
                        }

                        enqueue_success = queue_broker.enqueue(
                            queue_name=FUNDAMENTALS_QUEUE_NAME,
                            item_id=ticker,
                            data=queue_data,
                            ttl=FUNDAMENTALS_REDIS_TTL,
                        )

                        if enqueue_success:
                            time_series_len = len(time_series_dict.get("datetime", []))
                            summary_stats["time_series_rows"] += time_series_len
                            self.logger.debug(
                                f"{ticker}: Successfully enqueued {time_series_len} rows to Redis"
                            )
                        else:
                            self.logger.error(
                                f"{ticker}: Failed to enqueue time series data to Redis"
                            )
                            return {"success": False, "error": "Redis time series enqueue failed"}
                else:
                    summary_stats["static_rows"] += 1
                    summary_stats["time_series_rows"] += len(time_series_df)

                return {"success": True}

            except Exception as e:
                self.logger.error(f"{ticker}: Exception during processing: {e}")
                return {"success": False, "error": str(e)}

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
                            target=fetch_ticker_fundamentals,
                            name=f"fundamentals-{ticker}",
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
        thread_manager.wait_for_all_threads(timeout=300)

        summary = thread_manager.get_results_summary()
        summary_stats["successful"] = summary["successful"]
        summary_stats["failed"] = summary["failed"]

        thread_manager.cleanup_dead_threads()

        print_summary(summary_stats, write)
