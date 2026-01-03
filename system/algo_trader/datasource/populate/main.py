"""Populate market data from various sources.

This module provides CLI tools for populating market data from SEC and
other sources into InfluxDB for historical analysis.
"""

import argparse
from typing import ClassVar

from infrastructure.logging.logger import get_logger
from system.algo_trader.datasource.populate.fundamentals.handler import (
    FundamentalsArgumentHandler,
)
from system.algo_trader.datasource.populate.ohlcv.handler import (
    OHLCVArgumentHandler,
)


class PopulateCLI:
    """Command line interface for market data population.

    Provides argument parsing, handler orchestration, and workflow execution
    for populating market data from various sources.

    Attributes:
        logger: Logger instance for this CLI.
    """

    # Registry of all argument handlers
    ARGUMENT_HANDLERS: ClassVar[list[type]] = [
        OHLCVArgumentHandler,
        FundamentalsArgumentHandler,
    ]

    def __init__(self) -> None:
        """Initialize the populate CLI."""
        self.logger = get_logger(self.__class__.__name__)

    def run(self) -> None:
        """Execute the CLI workflow.

        Sets up argument parsing using registered handlers, processes arguments,
        and executes data population workflow.
        """
        self.logger.info("Starting market data population...")

        # Create argument parser
        parser = argparse.ArgumentParser(
            description="Populate market data from various sources into InfluxDB"
        )

        # Create subparsers for commands
        subparsers = parser.add_subparsers(
            dest="command", required=True, help="Data population command"
        )

        # Map handlers to their subcommand names
        handler_map = {}

        # Instantiate all handlers and create subcommands
        for handler_class in self.ARGUMENT_HANDLERS:
            handler = handler_class()
            # Get the subcommand name based on handler class name
            subcommand = handler_class.__name__.replace("ArgumentHandler", "").lower()
            subparser = subparsers.add_parser(
                subcommand, help=f"{subcommand.upper()} data population"
            )
            handler.add_arguments(subparser)
            handler_map[subcommand] = handler

        # Get flat list of all handlers for iteration
        handler_instances = list(handler_map.values())

        # Parse arguments
        args = parser.parse_args()

        # Process arguments using applicable handlers
        context = {}
        for handler in handler_instances:
            if handler.is_applicable(args):
                try:
                    result = handler.process(args)
                    context.update(result)
                    self.logger.info(f"Handler '{handler.name}' processed successfully")
                except Exception as e:
                    self.logger.error(f"Handler '{handler.name}' failed: {e}")
                    self.logger.error("Aborting data population")
                    return

        # Execute handler logic with processed context
        for handler in handler_instances:
            if handler.is_applicable(args):
                try:
                    handler.execute(context)
                    self.logger.info(f"Handler '{handler.name}' executed successfully")
                except Exception as e:
                    self.logger.error(f"Handler '{handler.name}' execution failed: {e}")
                    self.logger.error("Aborting data population")
                    return

        self.logger.info("Data population complete")


def main() -> None:
    """Main entry point for the populate script."""
    PopulateCLI().run()


if __name__ == "__main__":
    main()
