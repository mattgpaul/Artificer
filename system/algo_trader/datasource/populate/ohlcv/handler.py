"""OHLCV data population argument handler.

This module provides argument parsing and execution for OHLCV (Open, High,
Low, Close, Volume) data population from Schwab API.
"""

import argparse

from system.algo_trader.datasource.populate.argument_base import ArgumentHandler
from system.algo_trader.datasource.populate.ohlcv.processor import OHLCVProcessor
from system.algo_trader.datasource.populate.ohlcv.verifier import BadTickerVerifier
from system.algo_trader.datasource.sec.tickers.main import Tickers
from system.algo_trader.mysql.bad_ticker_client import BadTickerClient
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType
from system.algo_trader.strategy.utils.cli_utils import get_sp500_tickers


class OHLCVArgumentHandler(ArgumentHandler):
    """Handler for OHLCV data population command arguments.

    Processes command-line arguments for fetching and storing OHLCV price
    history data from Schwab API.
    """

    def __init__(self) -> None:
        """Initialize OHLCV argument handler."""
        super().__init__("ohlcv")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add OHLCV-specific arguments to parser.

        Args:
            parser: Argument parser to add arguments to.
        """
        parser.add_argument(
            "--tickers",
            nargs="+",
            required=False,
            help=(
                'List of ticker symbols to pull data for (e.g., "AAPL MSFT GOOGL"). '
                'Use "SP500" for S&P 500 tickers, "full-registry" to fetch all tickers from SEC datasource, '
                'or "missing-tickers" to fetch tickers from missing_tickers table. '
                "Required unless --verify-bad-tickers is used."
            ),
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
        parser.add_argument(
            "--verify-bad-tickers",
            action="store_true",
            help="Verify bad tickers in MySQL and remove them if they are no longer bad",
        )

    def is_applicable(self, args: argparse.Namespace) -> bool:
        """Check if this handler applies to the given arguments.

        Args:
            args: Parsed command-line arguments.

        Returns:
            True if command is 'ohlcv', False otherwise.
        """
        return hasattr(args, "command") and args.command == "ohlcv"

    def process(self, args: argparse.Namespace) -> dict:
        """Process and validate arguments for OHLCV command.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Dictionary containing processed tickers, frequency/period settings,
            and verify_bad_tickers flag.

        Raises:
            ValueError: If tickers are not provided and verify_bad_tickers is False,
                or if SEC datasource fails.
        """
        verify_bad_tickers = getattr(args, "verify_bad_tickers", False)
        tickers = args.tickers

        if not tickers and not verify_bad_tickers:
            raise ValueError("--tickers is required unless --verify-bad-tickers is used")

        if not tickers:
            tickers = []

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
        elif tickers == ["SP500"]:
            self.logger.info("SP500 specified, fetching S&P 500 tickers...")
            ticker_list = get_sp500_tickers()
            if not ticker_list:
                self.logger.error("Failed to retrieve S&P 500 tickers")
                raise ValueError("Failed to retrieve S&P 500 tickers")
            self.logger.info(f"Retrieved {len(ticker_list)} S&P 500 tickers")
            tickers = ticker_list
        elif tickers == ["missing-tickers"]:
            self.logger.info(
                "missing-tickers specified, fetching tickers from missing_tickers table..."
            )
            bad_ticker_client = BadTickerClient()
            tickers = bad_ticker_client.get_missing_tickers(limit=10000)
            if not tickers:
                self.logger.warning("No missing tickers found in MySQL")
                raise ValueError("No missing tickers found in missing_tickers table")
            self.logger.info(f"Retrieved {len(tickers)} missing tickers from MySQL")
        else:
            self.logger.info(f"Processing {len(tickers)} specific tickers: {tickers}")

        frequency_type = FrequencyType(args.frequency)
        period_type = PeriodType(args.period)

        if not frequency_type.is_valid_frequency(args.frequency_value):
            raise ValueError(
                f"Invalid frequency value {args.frequency_value} for {frequency_type.value}"
            )

        period_type.validate_combination(args.period_value, frequency_type, args.frequency_value)

        self.logger.info(
            f"Validated frequency: {frequency_type.value}={args.frequency_value}, "
            f"period: {period_type.value}={args.period_value}"
        )

        if tickers:
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
            "frequency_type": frequency_type,
            "frequency_value": args.frequency_value,
            "period_type": period_type,
            "period_value": args.period_value,
            "verify_bad_tickers": getattr(args, "verify_bad_tickers", False),
        }

    def execute(self, context: dict) -> None:
        """Execute OHLCV data population with processed context.

        Args:
            context: Dictionary containing tickers, frequency/period settings,
                and verify_bad_tickers flag.
        """
        frequency_type = context.get("frequency_type")
        frequency_value = context.get("frequency_value")
        period_type = context.get("period_type")
        period_value = context.get("period_value")
        verify_bad_tickers = context.get("verify_bad_tickers", False)

        if verify_bad_tickers:
            verifier = BadTickerVerifier(logger=self.logger)
            verifier.verify_bad_tickers(frequency_type, frequency_value, period_type, period_value)

        tickers = context.get("tickers")
        if tickers is None:
            if not verify_bad_tickers:
                self.logger.error("No tickers found in context")
            return

        processor = OHLCVProcessor(logger=self.logger)
        processor.process_tickers(
            tickers, frequency_type, frequency_value, period_type, period_value
        )
