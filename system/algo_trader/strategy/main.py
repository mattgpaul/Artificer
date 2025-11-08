#!/usr/bin/env python3
import argparse
import sys
from datetime import datetime, timedelta

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.cli_utils import (
    format_journal_summary,
    format_signal_summary,
    format_trade_details,
    resolve_tickers,
)
from system.algo_trader.strategy.journal import TradeJournal
from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy


def parse_args():
    parser = argparse.ArgumentParser(
        description="Trading strategy execution framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        required=True,
        help='Ticker symbols or "full-registry" for all SEC tickers',
    )

    parser.add_argument(
        "--threading",
        action="store_true",
        help="Enable multi-threaded processing (default: False)",
    )

    parser.add_argument(
        "--lookback",
        type=int,
        default=90,
        help="Days of historical data to analyze (default: 90)",
    )

    parser.add_argument(
        "--database",
        type=str,
        default="algo-trader-database",
        help="InfluxDB database name (default: algo-trader-database)",
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help="Write signals to InfluxDB (default: False)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit OHLCV records to fetch (default: no limit)",
    )

    parser.add_argument(
        "--journal",
        action="store_true",
        help="Generate trading journal after strategy execution (default: False)",
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Capital per trade for journal calculations (default: 10000)",
    )

    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=0.04,
        help="Risk-free rate for Sharpe ratio calculation (default: 0.04)",
    )

    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed trade-by-trade P&L in journal (default: False)",
    )

    subparsers = parser.add_subparsers(
        dest="strategy",
        required=True,
        help="Trading strategy to execute",
    )

    sma_parser = subparsers.add_parser(
        "sma-crossover",
        help="Simple Moving Average crossover strategy",
    )
    temp_strategy = SMACrossoverStrategy()
    temp_strategy.add_strategy_arguments(sma_parser)

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

    end_time = datetime.now()
    start_time = end_time - timedelta(days=args.lookback)
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Tickers: {len(tickers)} ticker(s)")
    logger.info(f"Time range: {start_time_str} to now ({args.lookback} days)")
    logger.info(f"Threading: {'enabled' if args.threading else 'disabled'}")
    logger.info(f"Database: {args.database}")
    logger.info(f"Write to DB: {args.write}")

    strategy = None
    try:
        if args.strategy == "sma-crossover":
            logger.info(
                f"Initializing SMA Crossover: short={args.short}, long={args.long}, "
                f"min_confidence={args.min_confidence}"
            )
            strategy = SMACrossoverStrategy(
                short_window=args.short,
                long_window=args.long,
                min_confidence=args.min_confidence,
                database=args.database,
                use_threading=args.threading,
            )
        else:
            logger.error(f"Unknown strategy: {args.strategy}")
            return 1

        if len(tickers) == 1:
            logger.info(f"Running strategy for single ticker: {tickers[0]}")
            signals = strategy.run_strategy(
                ticker=tickers[0],
                start_time=start_time_str,
                limit=args.limit,
                write_signals=args.write,
            )
        else:
            logger.info(f"Running strategy for {len(tickers)} tickers")
            signals = strategy.run_strategy_multi(
                tickers=tickers,
                start_time=start_time_str,
                limit=args.limit,
                write_signals=args.write,
            )

        if signals.empty:
            logger.warning("No trading signals were generated")
            logger.info("Possible reasons:")
            logger.info("  - Insufficient OHLCV data in InfluxDB")
            logger.info("  - No signal conditions detected in the time range")
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

            # Generate trading journal if requested
            if args.journal:
                logger.info("Generating trading journal...")

                # Process journal per ticker if multiple tickers
                unique_tickers = signals["ticker"].unique()

                for ticker in unique_tickers:
                    ticker_signals = signals[signals["ticker"] == ticker]

                    journal = TradeJournal(
                        signals=ticker_signals,
                        capital_per_trade=args.capital,
                        risk_free_rate=args.risk_free_rate,
                    )

                    metrics, trades = journal.generate_report()

                    # Display journal summary
                    print(format_journal_summary(metrics, ticker, args.strategy))

                    # Display detailed trades if requested
                    if args.detailed:
                        print(format_trade_details(trades))

    except ValueError as e:
        logger.error(f"Strategy initialization failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Strategy execution failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        if strategy:
            strategy.close()
            logger.info("Strategy execution complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
