"""OHLCV data processor.

This module provides processing logic for fetching and storing OHLCV price
history data from Schwab API.
"""

import datetime
import time

from infrastructure.config import ThreadConfig
from infrastructure.logging.logger import get_logger
from infrastructure.threads.thread_manager import ThreadManager
from system.algo_trader.redis.queue_broker import QueueBroker
from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType

OHLCV_QUEUE_NAME = "ohlcv_queue"
BAD_TICKER_QUEUE_NAME = "bad_ticker_queue"
OHLCV_REDIS_TTL = 3600
BAD_TICKER_REDIS_TTL = 3600
MAX_THREADS = 4


class OHLCVProcessor:
    """Processor for OHLCV data fetching and storage.

    Handles concurrent fetching of price history data and publishing to
    Redis queues for downstream processing.
    """

    def __init__(self, logger=None):
        """Initialize OHLCV processor.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def process_tickers(
        self,
        tickers: list[str],
        frequency_type: FrequencyType,
        frequency_value: int,
        period_type: PeriodType,
        period_value: int,
    ) -> None:
        """Process tickers to fetch and store OHLCV data.

        Args:
            tickers: List of ticker symbols to process.
            frequency_type: Frequency type for price history (minute, daily, etc.).
            frequency_value: Frequency value (e.g., 1 for daily, 5 for 5-minute).
            period_type: Period type for price history (day, month, year, etc.).
            period_value: Period value (e.g., 1 for 1 day, 12 for 12 months).
        """
        if tickers is None:
            self.logger.error("No tickers found")
            return

        self.logger.info(
            f"Executing OHLCV data population for {len(tickers)} tickers with "
            f"frequency {frequency_type.value}={frequency_value} "
            f"and period {period_type.value}={period_value}"
        )

        market_handler = MarketHandler()

        thread_config = ThreadConfig(max_threads=MAX_THREADS)
        thread_manager = ThreadManager(config=thread_config)

        queue_broker = QueueBroker(namespace="queue")

        max_threads = MAX_THREADS
        self.logger.info(f"ThreadManager initialized with max_threads={max_threads}")
        self.logger.info(f"QueueBroker initialized for queue: {OHLCV_QUEUE_NAME}")

        def enqueue_bad_ticker(ticker: str, reason: str) -> None:
            timestamp = datetime.datetime.utcnow().isoformat()
            bad_ticker_data = {
                "ticker": ticker,
                "timestamp": timestamp,
                "reason": reason,
            }
            queue_broker.enqueue(
                queue_name=BAD_TICKER_QUEUE_NAME,
                item_id=ticker,
                data=bad_ticker_data,
                ttl=BAD_TICKER_REDIS_TTL,
            )

        if len(tickers) > max_threads:
            self.logger.info(
                f"Ticker count ({len(tickers)}) exceeds max_threads ({max_threads}). "
                f"Batching will be used. Consider increasing THREAD_MAX_THREADS "
                f"for faster processing."
            )

        def fetch_ticker_data(ticker: str) -> dict:
            try:
                self.logger.debug(f"Fetching price history for {ticker}")

                response = market_handler.get_price_history(
                    ticker=ticker,
                    period_type=period_type,
                    period=period_value,
                    frequency_type=frequency_type,
                    frequency=frequency_value,
                )

                # Check for server errors (500/502) - these are NOT bad tickers
                if "_error_status" in response:
                    status_code = response.get("_error_status")
                    if status_code in (500, 502):
                        self.logger.error(
                            f"{ticker}: Server error {status_code} from API - "
                            "skipping (transient error, not a bad ticker)"
                        )
                        return {"success": False, "error": f"Server error {status_code}", "skip_bad_ticker": True}
                    else:
                        # Other errors (404, 400, etc.) might indicate bad ticker
                        self.logger.error(f"{ticker}: API error {status_code}")
                        enqueue_bad_ticker(ticker, f"API error {status_code}")
                        return {"success": False, "error": f"API error {status_code}"}

                if not response:
                    self.logger.error(f"{ticker}: Empty response from API")
                    enqueue_bad_ticker(ticker, "Empty response")
                    return {"success": False, "error": "Empty response"}

                if "candles" not in response:
                    self.logger.error(f"{ticker}: No candles data in response")
                    enqueue_bad_ticker(ticker, "No candles data")
                    return {"success": False, "error": "No candles data"}

                candles = response["candles"]
                if not candles:
                    self.logger.warning(f"{ticker}: Candles list is empty")
                    enqueue_bad_ticker(ticker, "Empty candles list")
                    return {"success": False, "error": "Empty candles list"}

                queue_data = {
                    "ticker": ticker,
                    "candles": candles,
                    "frequency_type": frequency_type.value,
                    "frequency_value": frequency_value,
                    "period_type": period_type.value,
                    "period_value": period_value,
                }

                enqueue_success = queue_broker.enqueue(
                    queue_name=OHLCV_QUEUE_NAME,
                    item_id=ticker,
                    data=queue_data,
                    ttl=OHLCV_REDIS_TTL,
                )

                if enqueue_success:
                    self.logger.debug(
                        f"{ticker}: Successfully enqueued {len(candles)} candles to Redis"
                    )
                    return {"success": True}
                else:
                    self.logger.error(f"{ticker}: Failed to enqueue data to Redis")
                    return {"success": False, "error": "Redis enqueue failed"}

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
                            target=fetch_ticker_data,
                            name=f"ohlcv-{ticker}",
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
        self.logger.info(
            f"Batch processing complete: {summary['successful']} successful, "
            f"{summary['failed']} failed out of {len(tickers)} total tickers"
        )

        thread_manager.cleanup_dead_threads()

        print(f"\n{'=' * 50}")
        print("OHLCV Data Fetching Summary")
        print(f"{'=' * 50}")
        print(f"Total Tickers: {len(tickers)}")
        print(f"Successfully Enqueued: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Queue: {OHLCV_QUEUE_NAME}")
        print(f"Redis TTL: {OHLCV_REDIS_TTL}s")
        print("\nData will be published to InfluxDB by the influx-publisher service.")
        print(f"{'=' * 50}\n")
