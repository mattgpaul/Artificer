#!/usr/bin/env python3
"""Unified market data service CLI with subcommand-based service selection."""

import argparse
import sys

from system.algo_trader.config import AlgoTraderConfig
from system.algo_trader.service.market_data.historical import HistoricalMarketService
from system.algo_trader.service.market_data.live import LiveMarketService


def main() -> int:
    """Main entry point for market data services.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    parser = argparse.ArgumentParser(
        description="Market Data Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s live run                    # Run live market data service
  %(prog)s live health                 # Check live service health
  %(prog)s historical run              # Run historical data collection
  %(prog)s historical health           # Check historical service health
  %(prog)s live run --sleep-interval 5 # Run live service with 5s intervals
        """,
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file (optional, uses environment variables by default)",
    )

    subparsers = parser.add_subparsers(dest="service", required=True, help="Service to run")

    # Live market subcommand
    live_parser = subparsers.add_parser("live", help="Run live market data service")
    live_parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "health"],
        help="Command to execute (default: run)",
    )
    live_parser.add_argument(
        "--sleep-interval",
        type=int,
        help="Override sleep interval in seconds (default: auto-detect based on market hours)",
    )

    # Historical market subcommand
    historical_parser = subparsers.add_parser(
        "historical", help="Run historical market data service"
    )
    historical_parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "health"],
        help="Command to execute (default: run)",
    )

    args = parser.parse_args()

    try:
        # Load configuration
        config: AlgoTraderConfig | None = None
        if args.config:
            # TODO: Implement config file loading if needed
            print(f"Config file loading not yet implemented: {args.config}")
            return 1
        else:
            config = AlgoTraderConfig.from_env()

        # Select service class and configuration
        if args.service == "live":
            service = LiveMarketService(
                sleep_override=getattr(args, "sleep_interval", None), config=config
            )
        elif args.service == "historical":
            service = HistoricalMarketService(config=config)
        else:
            print(f"Unknown service: {args.service}")
            return 1

        # Execute command
        if args.command == "run":
            service.run()
            return 0
        elif args.command == "health":
            health_passed = service.health_check()
            if health_passed:
                service.logger.info("Health check passed")
            else:
                service.logger.error("Health check failed")
            return 0 if health_passed else 1

    except KeyboardInterrupt:
        print("Service interrupted by user")
        return 0
    except Exception as e:
        print(f"Service failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
