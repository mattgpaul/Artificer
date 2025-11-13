"""Fundamentals data population handler.

This module provides argument handling and execution for populating fundamentals
data from SEC company facts API into Redis queues and MySQL database.
"""

import argparse
import time

import pandas as pd

from infrastructure.config import ThreadConfig
from infrastructure.threads.thread_manager import ThreadManager
from system.algo_trader.datasource.populate.argument_base import ArgumentHandler
from system.algo_trader.datasource.sec.tickers import Tickers
from system.algo_trader.mysql.bad_ticker_client import BadTickerClient
from system.algo_trader.redis.queue_broker import QueueBroker

FUNDAMENTALS_QUEUE_NAME = "fundamentals_queue"
FUNDAMENTALS_STATIC_QUEUE_NAME = "fundamentals_static_queue"
FUNDAMENTALS_REDIS_TTL = 3600
MAX_THREADS = 4


class FundamentalsArgumentHandler(ArgumentHandler):
    """Handler for fundamentals data population arguments and execution.

    Processes command-line arguments for fetching company fundamentals data
    from SEC API and enqueuing it to Redis for downstream processing.
    """

    def __init__(self) -> None:
        """Initialize FundamentalsArgumentHandler with 'fundamentals' command name."""
        super().__init__("fundamentals")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-line arguments for fundamentals data population.

        Args:
            parser: ArgumentParser instance to add arguments to.
        """
        parser.add_argument(
            "--tickers",
            nargs="+",
            required=False,
            help='List of ticker symbols to pull data for (e.g., "AAPL MSFT GOOGL"). '
            'Use "full-registry" to fetch all tickers from SEC datasource.',
        )
        parser.add_argument(
            "--lookback-period",
            type=int,
            default=10,
            help="Number of years to look back for company facts data. Default: 10",
        )
        parser.add_argument(
            "--write",
            action="store_true",
            default=False,
            help="If set, write data to MySQL and Redis. If not set, dry-run mode (no writes).",
        )
        parser.add_argument(
            "--max-threads",
            type=int,
            default=4,
            help="Maximum number of threads for concurrent processing. Default: 4",
        )

    def is_applicable(self, args: argparse.Namespace) -> bool:
        """Check if this handler applies to the given arguments.

        Args:
            args: Parsed command-line arguments.

        Returns:
            True if command is 'fundamentals', False otherwise.
        """
        return hasattr(args, "command") and args.command == "fundamentals"

    def process(self, args: argparse.Namespace) -> dict:
        """Process command-line arguments and prepare execution context.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Dictionary containing processed tickers, lookback period, write flag,
            and max_threads configuration.

        Raises:
            ValueError: If tickers are not provided or SEC datasource fails.
        """
        tickers = args.tickers

        if not tickers:
            raise ValueError("--tickers is required")

        if tickers == ["full-registry"]:
            self.logger.info("full-registry specified, fetching all tickers from SEC datasource...")
            ticker_source = Tickers()
            all_tickers_data = ticker_source.get_tickers()

            if all_tickers_data is None:
                self.logger.error("Failed to retrieve tickers from SEC")
                raise ValueError("Failed to retrieve tickers from SEC datasource")

            ticker_list = []
            for _key, value in all_tickers_data.items():
                if isinstance(value, dict) and "ticker" in value:
                    ticker_list.append(value["ticker"])

            self.logger.info(f"Retrieved {len(ticker_list)} tickers from SEC datasource")
            tickers = ticker_list
        else:
            self.logger.info(f"Processing {len(tickers)} specific tickers: {tickers}")

        bad_ticker_client = BadTickerClient()
        original_count = len(tickers)
        filtered_tickers = [
            ticker for ticker in tickers if not bad_ticker_client.is_bad_ticker(ticker)
        ]
        filtered_count = original_count - len(filtered_tickers)
        if filtered_count > 0:
            self.logger.info(f"Filtered out {filtered_count} bad tickers from MySQL")
        tickers = filtered_tickers

        return {
            "tickers": tickers,
            "lookback_period": args.lookback_period,
            "write": getattr(args, "write", False),
            "max_threads": args.max_threads,
        }

    def execute(self, context: dict) -> None:  # noqa: C901, PLR0915
        """Execute fundamentals data population for given tickers.

        Fetches company facts data from SEC API and enqueues to Redis queues
        for downstream processing. Uses thread pool for concurrent processing.

        Args:
            context: Dictionary containing:
                - tickers: List of ticker symbols to process
                - lookback_period: Years of historical data to fetch (default: 10)
                - write: Whether to write to Redis (default: False)
                - max_threads: Maximum concurrent threads (default: 4)
        """
        tickers = context.get("tickers")
        lookback_period = context.get("lookback_period", 10)
        write = context.get("write", False)
        max_threads = context.get("max_threads", MAX_THREADS)

        if tickers is None:
            self.logger.error("No tickers found in context")
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

                # Count market_cap rows (market_cap is already in DataFrame
                # from SEC data extraction)
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

                        time_series_dict = self._dataframe_to_dict(time_series_df)
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

        self._print_summary(summary_stats, write)

    def _dataframe_to_dict(self, df: pd.DataFrame) -> dict:
        df_copy = df.copy()

        if isinstance(df_copy.index, pd.DatetimeIndex):
            datetime_ms = (df_copy.index.astype("int64") // 10**6).tolist()
        elif "time" in df_copy.columns:
            datetime_ms = (pd.to_datetime(df_copy["time"]).astype("int64") // 10**6).tolist()
            df_copy = df_copy.drop("time", axis=1)
        else:
            datetime_ms = (pd.to_datetime(df_copy.index).astype("int64") // 10**6).tolist()

        df_copy = df_copy.reset_index(drop=True)
        result = df_copy.to_dict("list")
        result["datetime"] = datetime_ms

        return result

    def _print_summary(self, stats: dict, write: bool) -> None:
        print(f"\n{'=' * 50}")
        print("Fundamentals Data Fetching Summary")
        print(f"{'=' * 50}")
        print(f"Total Tickers: {stats['total']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Static Data Rows: {stats['static_rows']}")
        print(f"Time Series Rows: {stats['time_series_rows']}")
        print(f"Market Cap Rows: {stats['market_cap_rows']}")
        if write:
            print(f"Time Series Queue: {FUNDAMENTALS_QUEUE_NAME}")
            print(f"Static Data Queue: {FUNDAMENTALS_STATIC_QUEUE_NAME}")
            print(f"Redis TTL: {FUNDAMENTALS_REDIS_TTL}s")
            print(
                "\nTime series data will be published to InfluxDB by the influx-publisher service."
            )
            print("Static data will be written to MySQL by the mysql-daemon service.")
        else:
            print("\nDry-run mode: No data was written to MySQL or Redis.")
        print(f"{'=' * 50}\n")
