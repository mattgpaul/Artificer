"""OHLCV data argument handler for population scripts.

Provides argument parsing and validation for OHLCV (Open, High, Low, Close, Volume)
data population with validation against Schwab API timescale requirements.
"""

import argparse
import time

from infrastructure.influxdb.influxdb import BatchWriteConfig
from infrastructure.threads.thread_manager import ThreadManager
from system.algo_trader.datasource.populate.argument_base import ArgumentHandler
from system.algo_trader.datasource.sec.tickers import Tickers
from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType

# InfluxDB batch write configurations for OHLCV data population
# Choose based on your use case:
#
# CONSERVATIVE: Best for multi-threaded safety with many concurrent threads
# - Lower memory footprint, more frequent flushes
# - Use for: High thread counts, limited memory environments
# ohlcv_write_config = BatchWriteConfig(
#     batch_size=500,
#     flush_interval=3000,
#     jitter_interval=500,
#     retry_interval=10000,
#     max_retries=3,
#     max_retry_delay=30000,
#     exponential_base=2,
# )
#
# BALANCED (RECOMMENDED): Good compromise between throughput and resource usage
# - Moderate memory usage, reasonable flush intervals
# - Use for: Most scenarios, 100-1000 tickers
ohlcv_write_config = BatchWriteConfig(
    batch_size=2000,
    flush_interval=5000,
    jitter_interval=1000,
    retry_interval=10000,
    max_retries=3,
    max_retry_delay=30000,
    exponential_base=2,
)
#
# AGGRESSIVE: Maximum throughput for bulk historical data loading
# - Higher memory usage, longer flush intervals, fewer network calls
# - Use for: full-registry runs (1000+ tickers), batch processing
# ohlcv_write_config = BatchWriteConfig(
#     batch_size=5000,
#     flush_interval=10000,
#     jitter_interval=2000,
#     retry_interval=15000,
#     max_retries=5,
#     max_retry_delay=30000,
#     exponential_base=2,
# )


class OHLCVArgumentHandler(ArgumentHandler):
    """Handler for OHLCV data population command line arguments.

    Provides functionality to:
    - Accept ticker symbols via --tickers argument
    - Fetch all tickers from SEC datasource using "full-registry" keyword
    - Validate frequency and period combinations against Schwab API requirements
    - Handle the ALL ticker symbol (Allstate) without confusion

    Designed to be thread-safe for future multi-threaded data fetching.

    Example:
        >>> handler = OHLCVArgumentHandler()
        >>> parser = argparse.ArgumentParser()
        >>> subparsers = parser.add_subparsers(dest="command")
        >>> ohlcv_parser = subparsers.add_parser("ohlcv")
        >>> handler.add_arguments(ohlcv_parser)
        >>> args = parser.parse_args(
        ...     ["ohlcv", "--tickers", "AAPL", "--frequency", "daily", "--period", "year"]
        ... )
        >>> result = handler.process(args, get_logger("test"))
    """

    def __init__(self) -> None:
        """Initialize OHLCV argument handler."""
        super().__init__("ohlcv")  # Display name for subcommand

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add OHLCV arguments to the parser.

        Args:
            parser: Argument parser to add arguments to (should be a subparser).
        """
        parser.add_argument(
            "--tickers",
            nargs="+",
            required=True,
            help='List of ticker symbols to pull data for (e.g., "AAPL MSFT GOOGL"). '
            'Use "full-registry" to fetch all tickers from SEC datasource.',
        )
        parser.add_argument(
            "--frequency",
            choices=[ft.value for ft in FrequencyType],
            default="daily",
            help=(
                "Frequency type for price history (minute, daily, weekly, monthly). Default: daily"
            ),
        )
        parser.add_argument(
            "--period",
            choices=[pt.value for pt in PeriodType],
            default="year",
            help="Period type for price history (day, month, year, ytd). Default: year",
        )
        parser.add_argument(
            "--frequency-value",
            type=int,
            default=1,
            help="Frequency value (e.g., 1 for daily, 5 for 5-minute). Default: 1",
        )
        parser.add_argument(
            "--period-value",
            type=int,
            default=10,
            help="Period value (e.g., 1 for 1 day, 12 for 12 months). Default: 10",
        )

    def is_applicable(self, args: argparse.Namespace) -> bool:
        """Check if OHLCV arguments are present.

        Args:
            args: Parsed arguments from argparse.

        Returns:
            True if command is "ohlcv".
        """
        return hasattr(args, "command") and args.command == "ohlcv"

    def process(self, args: argparse.Namespace) -> dict:
        """Process OHLCV arguments and validate against Schwab API requirements.

        Handles both specific ticker lists and fetching all available tickers
        from the SEC datasource when "full-registry" is provided.
        Validates frequency and period combinations.

        Args:
            args: Parsed command line arguments.

        Returns:
            Dictionary containing validated arguments.

        Raises:
            ValueError: If argument validation fails or ticker retrieval fails.
        """
        tickers = args.tickers

        # Check if user requested full registry fetch
        if tickers == ["full-registry"]:
            self.logger.info("full-registry specified, fetching all tickers from SEC datasource...")
            ticker_source = Tickers()
            all_tickers_data = ticker_source.get_tickers()

            if all_tickers_data is None:
                self.logger.error("Failed to retrieve tickers from SEC")
                raise ValueError("Failed to retrieve tickers from SEC datasource")

            # Extract ticker symbols from SEC data
            # SEC data structure: {"0": {"cik_str": 123, "ticker": "AAPL", "title": "..."}, ...}
            ticker_list = []
            for _key, value in all_tickers_data.items():
                if isinstance(value, dict) and "ticker" in value:
                    ticker_list.append(value["ticker"])

            self.logger.info(f"Retrieved {len(ticker_list)} tickers from SEC datasource")
            tickers = ticker_list
        else:
            # Return the provided list of tickers (could include "ALL" for Allstate)
            self.logger.info(f"Processing {len(tickers)} specific tickers: {tickers}")

        # Validate frequency and period
        frequency_type = FrequencyType(args.frequency)
        period_type = PeriodType(args.period)

        # Check frequency value is valid for frequency type
        if not frequency_type.is_valid_frequency(args.frequency_value):
            raise ValueError(
                f"Invalid frequency value {args.frequency_value} for {frequency_type.value}"
            )

        # Check period/frequency combination is valid
        period_type.validate_combination(args.period_value, frequency_type, args.frequency_value)

        self.logger.info(
            f"Validated frequency: {frequency_type.value}={args.frequency_value}, "
            f"period: {period_type.value}={args.period_value}"
        )

        return {
            "tickers": tickers,
            "frequency_type": frequency_type,
            "frequency_value": args.frequency_value,
            "period_type": period_type,
            "period_value": args.period_value,
        }

    def execute(self, context: dict) -> None:  # noqa: PLR0915, C901
        """Execute OHLCV data population with multi-threaded data fetching.

        Uses ThreadManager to fetch historical market data concurrently for multiple
        tickers. Automatically batches requests when ticker count exceeds max_threads.
        Displays statistics for each ticker and summary results.

        Args:
            context: Dictionary containing processed results from all handlers.
        """
        tickers = context.get("tickers")
        if tickers is None:
            self.logger.error("No tickers found in context")
            return

        frequency_type = context.get("frequency_type")
        frequency_value = context.get("frequency_value")
        period_type = context.get("period_type")
        period_value = context.get("period_value")

        self.logger.info(
            f"Executing OHLCV data population for {len(tickers)} tickers with "
            f"frequency {frequency_type.value}={frequency_value} "
            f"and period {period_type.value}={period_value}"
        )

        # Initialize MarketHandler, ThreadManager, and InfluxDB client
        market_handler = MarketHandler()
        thread_manager = ThreadManager()  # Uses config from environment
        influx_client = MarketDataInflux(
            database="algo-trader-database", write_config=ohlcv_write_config
        )  # Uses INFLUXDB_DATABASE env var

        max_threads = thread_manager.config.max_threads
        self.logger.info(f"ThreadManager initialized with max_threads={max_threads}")
        self.logger.info(f"InfluxDB client initialized for database: {influx_client.database}")

        # Track failed tickers with reasons for detailed reporting
        failed_tickers: list[tuple[str, str]] = []  # List of (ticker, reason) tuples

        # Check if batching will be needed
        if len(tickers) > max_threads:
            self.logger.info(
                f"Ticker count ({len(tickers)}) exceeds max_threads ({max_threads}). "
                f"Batching will be used. Consider increasing THREAD_MAX_THREADS "
                f"for faster processing."
            )

        def fetch_ticker_data(ticker: str) -> dict:
            """Thread target function to fetch OHLCV data and write to InfluxDB.

            Args:
                ticker: Stock symbol to fetch data for.

            Returns:
                Dictionary with 'success' boolean and optional 'error' message.
            """
            try:
                self.logger.debug(f"Fetching price history for {ticker}")

                # Fetch price history from Schwab API
                response = market_handler.get_price_history(
                    ticker=ticker,
                    period_type=period_type,
                    period=period_value,
                    frequency_type=frequency_type,
                    frequency=frequency_value,
                )

                # Check for empty or invalid response
                if not response:
                    error_msg = "Empty response from API"
                    self.logger.error(f"{ticker}: {error_msg}")
                    failed_tickers.append((ticker, error_msg))
                    return {"success": False, "error": error_msg}

                if "candles" not in response:
                    error_msg = "No candles data in response"
                    self.logger.error(f"{ticker}: {error_msg}")
                    failed_tickers.append((ticker, error_msg))
                    return {"success": False, "error": error_msg}

                candles = response["candles"]
                if not candles:
                    error_msg = "No data available (empty candles list)"
                    self.logger.warning(f"{ticker}: {error_msg}")
                    failed_tickers.append((ticker, error_msg))
                    return {"success": False, "error": error_msg}

                # Write data to InfluxDB
                write_success = influx_client.write(data=candles, ticker=ticker, table="ohlcv")

                if write_success:
                    self.logger.debug(
                        f"{ticker}: Successfully wrote {len(candles)} candles to InfluxDB"
                    )
                    return {"success": True}
                else:
                    error_msg = "InfluxDB write failed"
                    self.logger.error(f"{ticker}: {error_msg}")
                    failed_tickers.append((ticker, error_msg))
                    return {"success": False, "error": error_msg}

            except Exception as e:
                error_msg = f"Exception: {type(e).__name__}: {e!s}"
                self.logger.error(f"{ticker}: {error_msg}")
                failed_tickers.append((ticker, error_msg))
                return {"success": False, "error": str(e)}

        # Batch processing loop
        remaining_tickers = list(tickers)
        last_log_time = time.time()

        self.logger.info("Starting batch processing...")

        while remaining_tickers:
            # Check available thread capacity
            active_count = thread_manager.get_active_thread_count()
            available_slots = max_threads - active_count

            # Start new threads up to available capacity
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
                        remaining_tickers.append(ticker)  # Re-add to queue

            # Wait briefly for threads to complete
            time.sleep(0.5)

            # Log progress periodically (every 10 seconds)
            # Note: We don't cleanup dead threads here to preserve results for final summary
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

        # Wait for all remaining threads to complete
        self.logger.info("Waiting for all threads to complete...")
        thread_manager.wait_for_all_threads(timeout=300)

        # Get results summary BEFORE cleanup (cleanup removes threads from registry!)
        summary = thread_manager.get_results_summary()
        self.logger.info(
            f"Batch processing complete: {summary['successful']} successful, "
            f"{summary['failed']} failed out of {len(tickers)} total tickers"
        )

        # Final cleanup
        thread_manager.cleanup_dead_threads()

        # Wait for all batch writes to complete using closed-loop monitoring
        # This tracks the actual pending batch count rather than using fixed sleep time
        self.logger.info("Waiting for all batch writes to complete...")
        # Use dynamic timeout calculated from write config (None = auto-calculate)
        batches_complete = influx_client.wait_for_batches(timeout=None)

        if batches_complete:
            self.logger.info("All OHLCV data batches written successfully to InfluxDB.")
        else:
            self.logger.warning(
                "Some batches may still be pending after timeout. "
                "Data may still be written in background."
            )

        # Print final summary
        print(f"\n{'=' * 50}")
        print("OHLCV Data Population Summary")
        print(f"{'=' * 50}")
        print(f"Total Tickers: {len(tickers)}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"{'=' * 50}")

        # Print detailed failure information if any tickers failed
        if failed_tickers:
            print(f"\nFailed Tickers ({len(failed_tickers)}):")
            print(f"{'-' * 50}")
            for ticker, reason in failed_tickers:
                print(f"  {ticker:10s} - {reason}")
            print(f"{'-' * 50}")
        print()
