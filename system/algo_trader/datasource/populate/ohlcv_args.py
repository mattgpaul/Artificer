"""OHLCV data argument handler for population scripts.

Provides argument parsing and validation for OHLCV (Open, High, Low, Close, Volume)
data population with validation against Schwab API timescale requirements.
"""

import argparse

from system.algo_trader.datasource.populate.argument_base import ArgumentHandler
from system.algo_trader.datasource.sec.tickers import Tickers
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


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

    def execute(self, context: dict) -> None:
        """Execute OHLCV data population logic.

        Designed to be thread-safe for future multi-threaded implementation.

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

        # TODO: Implement thread-safe data fetching and persistence logic
        for ticker in tickers:
            self.logger.info(f"Processing {ticker}")
            # Add logic to fetch and store OHLCV data for each ticker
