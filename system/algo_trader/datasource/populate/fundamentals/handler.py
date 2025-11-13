"""Fundamentals data population argument handler.

This module provides argument parsing and execution for fundamentals data
population from SEC company facts API.
"""

import argparse

from system.algo_trader.datasource.populate.argument_base import ArgumentHandler
from system.algo_trader.datasource.populate.fundamentals.processor import FundamentalsProcessor
from system.algo_trader.datasource.sec.tickers.main import Tickers
from system.algo_trader.mysql.bad_ticker_client import BadTickerClient

MAX_THREADS = 4


class FundamentalsArgumentHandler(ArgumentHandler):
    """Handler for fundamentals data population command arguments.

    Processes command-line arguments for fetching and storing company
    fundamentals data from SEC company facts API.
    """

    def __init__(self) -> None:
        """Initialize fundamentals argument handler."""
        super().__init__("fundamentals")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add fundamentals-specific arguments to parser.

        Args:
            parser: Argument parser to add arguments to.
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
        """Process and validate arguments for fundamentals command.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Dictionary containing processed tickers, lookback period, write flag,
            and max threads.

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

        write = getattr(args, "write", False)
        if write:
            try:
                bad_ticker_client = BadTickerClient()
                original_count = len(tickers)
                filtered_tickers = [
                    ticker for ticker in tickers if not bad_ticker_client.is_bad_ticker(ticker)
                ]
                filtered_count = original_count - len(filtered_tickers)
                if filtered_count > 0:
                    self.logger.info(f"Filtered out {filtered_count} bad tickers from MySQL")
                tickers = filtered_tickers
            except Exception as e:
                self.logger.warning(f"Could not connect to MySQL for bad ticker filtering: {e}")
                self.logger.warning("Continuing without bad ticker filtering")

        return {
            "tickers": tickers,
            "lookback_period": args.lookback_period,
            "write": getattr(args, "write", False),
            "max_threads": args.max_threads,
        }

    def execute(self, context: dict) -> None:
        """Execute fundamentals data population with processed context.

        Args:
            context: Dictionary containing tickers, lookback_period, write flag,
                and max_threads.
        """
        tickers = context.get("tickers")
        lookback_period = context.get("lookback_period", 10)
        write = context.get("write", False)
        max_threads = context.get("max_threads", MAX_THREADS)

        processor = FundamentalsProcessor(logger=self.logger)
        processor.process_tickers(tickers, lookback_period, write, max_threads)
