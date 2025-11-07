#!/usr/bin/env python3
"""Demo script for SMA Crossover strategy.

This script demonstrates how to use the SMACrossoverStrategy to generate
trading signals. It can be run with different tickers and time ranges to
explore the strategy's behavior.

Usage:
    bazel run //system/algo_trader/strategy:sma_crossover_demo
    bazel run //system/algo_trader/strategy:sma_crossover_demo -- --ticker MSFT
    bazel run //system/algo_trader/strategy:sma_crossover_demo -- --ticker AAPL --short 5 --long 15
"""

import argparse
import sys
from datetime import datetime, timedelta

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Demo SMA Crossover trading strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--ticker",
        type=str,
        default="AAPL",
        help="Stock ticker symbol to analyze (default: AAPL)",
    )

    parser.add_argument(
        "--short",
        type=int,
        default=10,
        help="Short-term SMA window (default: 10)",
    )

    parser.add_argument(
        "--long",
        type=int,
        default=20,
        help="Long-term SMA window (default: 20)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence threshold for signals (default: 0.0)",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days of historical data to analyze (default: 90)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of OHLCV records to fetch (default: no limit)",
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help="Write signals to InfluxDB (default: False, just display)",
    )

    parser.add_argument(
        "--multi",
        nargs="+",
        help="Run strategy for multiple tickers (space-separated)",
    )

    parser.add_argument(
        "--threading",
        action="store_true",
        help="Enable multi-threaded processing for multiple tickers",
    )

    return parser.parse_args()


def format_signal_summary(signals):
    """Format signals DataFrame for pretty printing."""
    if signals.empty:
        return "No signals generated"

    output = []
    output.append(f"\n{'=' * 80}")
    output.append(f"Generated {len(signals)} trading signals")
    output.append(f"{'=' * 80}\n")

    for _, row in signals.iterrows():
        signal_time = row["signal_time"].strftime("%Y-%m-%d %H:%M:%S")
        signal_type = row["signal_type"].upper()
        price = row["price"]
        confidence = row.get("confidence", 0.0)
        ticker = row.get("ticker", "N/A")

        output.append(
            f"[{signal_time}] {ticker} - {signal_type:4s} @ ${price:.2f} "
            f"(confidence: {confidence:.2%})"
        )

    output.append(f"\n{'=' * 80}")

    # Summary statistics
    buy_count = (signals["signal_type"] == "buy").sum()
    sell_count = (signals["signal_type"] == "sell").sum()
    avg_confidence = signals.get("confidence", 0.0).mean()

    output.append(f"Summary: {buy_count} BUY signals, {sell_count} SELL signals")
    output.append(f"Average confidence: {avg_confidence:.2%}")
    output.append(f"{'=' * 80}\n")

    return "\n".join(output)


def main():
    """Run SMA crossover strategy demo."""
    args = parse_args()
    logger = get_logger("SMACrossoverDemo")

    logger.info("=" * 80)
    logger.info("SMA Crossover Strategy Demo")
    logger.info("=" * 80)

    # Calculate start time based on days parameter
    end_time = datetime.now()
    start_time = end_time - timedelta(days=args.days)
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Initialize strategy
    logger.info(f"Initializing strategy with short={args.short}, long={args.long}")
    try:
        strategy = SMACrossoverStrategy(
            short_window=args.short,
            long_window=args.long,
            min_confidence=args.min_confidence,
            use_threading=args.threading,
        )
    except ValueError as e:
        logger.error(f"Invalid strategy parameters: {e}")
        return 1

    # Run strategy for single or multiple tickers
    if args.multi:
        tickers = args.multi
        logger.info(f"Running strategy for {len(tickers)} tickers: {', '.join(tickers)}")
        logger.info(f"Time range: {start_time_str} to now ({args.days} days)")
        logger.info(f"Threading: {'enabled' if args.threading else 'disabled'}")

        signals = strategy.run_strategy_multi(
            tickers=tickers,
            start_time=start_time_str,
            limit=args.limit,
        )
    else:
        ticker = args.ticker
        logger.info(f"Running strategy for {ticker}")
        logger.info(f"Time range: {start_time_str} to now ({args.days} days)")

        signals = strategy.run_strategy(
            ticker=ticker,
            start_time=start_time_str,
            limit=args.limit,
        )

    # Display results
    if signals.empty:
        logger.warning("No trading signals were generated")
        logger.info("Possible reasons:")
        logger.info("  - Insufficient OHLCV data in InfluxDB")
        logger.info("  - No crossovers detected in the time range")
        logger.info("  - All signals below min_confidence threshold")
        logger.info("\nTo populate OHLCV data, run:")
        logger.info("  bazel run //system/algo_trader/datasource/populate:main")
    else:
        print(format_signal_summary(signals))

        if not args.write:
            logger.info("NOTE: Signals were NOT written to InfluxDB")
            logger.info("To persist signals, run with --write flag")
        else:
            logger.info("Signals have been written to InfluxDB strategy table")

    # Cleanup
    strategy.close()
    logger.info("Strategy demo complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
