#!/usr/bin/env python3
"""Unified market data service CLI with subcommand-based service selection."""

import argparse
import sys

from system.algo_trader.market_data.historical import HistoricalMarketService
from system.algo_trader.market_data.live import LiveMarketService


def main():
    """Main entry point for market data services."""
    parser = argparse.ArgumentParser(description="Market Data Service")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )

    subparsers = parser.add_subparsers(dest="service", required=True, help="Service to run")

    # Live market subcommand
    live_parser = subparsers.add_parser("live", help="Run live market data service")
    live_parser.add_argument(
        "command", nargs="?", default="run", choices=["run", "health"], help="Command to execute"
    )
    live_parser.add_argument(
        "--sleep-interval", type=int, help="Override sleep interval in seconds"
    )

    # Historical market subcommand
    historical_parser = subparsers.add_parser(
        "historical", help="Run historical market data service"
    )
    historical_parser.add_argument(
        "command", nargs="?", default="run", choices=["run", "health"], help="Command to execute"
    )

    args = parser.parse_args()

    try:
        # Select service class and configuration
        if args.service == "live":
            service = LiveMarketService(sleep_override=getattr(args, "sleep_interval", None))
        elif args.service == "historical":
            service = HistoricalMarketService()

        # Execute command
        if args.command == "run":
            service.run()
            return 0
        elif args.command == "health":
            if service.health_check():
                service.logger.info("Health check passed")
                return 0
            else:
                service.logger.error("Health check failed")
                return 1

    except KeyboardInterrupt:
        print("Service interrupted by user")
        return 0
    except Exception as e:
        print(f"Service failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
