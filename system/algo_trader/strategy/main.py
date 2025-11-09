#!/usr/bin/env python3
import argparse
import sys

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.cli_utils import resolve_tickers
from system.algo_trader.strategy.executor import execute_strategy
from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy


def parse_args():
    parser = argparse.ArgumentParser(
        description="Trading strategy execution framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--tickers", nargs="+", required=True,
                        help='Ticker symbols or "full-registry" for all SEC tickers')
    parser.add_argument("--threading", action="store_true",
                        help="Enable multi-threaded processing (default: False)")
    parser.add_argument("--lookback", type=int, default=90,
                        help="Days of historical data to analyze (default: 90)")
    parser.add_argument("--database", type=str, default="algo-trader-database",
                        help="InfluxDB database name (default: algo-trader-database)")
    parser.add_argument("--write", action="store_true",
                        help="Write signals to InfluxDB (default: False)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit OHLCV records to fetch (default: no limit)")
    parser.add_argument("--journal", action="store_true",
                        help="Generate trading journal after strategy execution (default: False)")
    parser.add_argument("--capital", type=float, default=10000.0,
                        help="Capital per trade for journal calculations (default: 10000)")
    parser.add_argument("--risk-free-rate", type=float, default=0.04,
                        help="Risk-free rate for Sharpe ratio calculation (default: 0.04)")
    parser.add_argument("--detailed", action="store_true",
                        help="Show detailed trade-by-trade P&L in journal (default: False)")

    subparsers = parser.add_subparsers(dest="strategy", required=True,
                                        help="Trading strategy to execute")
    sma_parser = subparsers.add_parser("sma-crossover",
                                        help="Simple Moving Average crossover strategy")
    SMACrossoverStrategy().add_strategy_arguments(sma_parser)

    return parser.parse_args()


def main():
    args = parse_args()
    logger = get_logger("StrategyMain")

    logger.info("=" * 80)
    logger.info("Trading Strategy Execution")
    logger.info("=" * 80)

    try:
        tickers = resolve_tickers(args.tickers, logger)
    except ValueError as e:
        logger.error(f"Failed to resolve tickers: {e}")
        return 1

    return execute_strategy(args, tickers, logger)


if __name__ == "__main__":
    sys.exit(main())
