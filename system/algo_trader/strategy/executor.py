from datetime import datetime, timedelta

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.cli_utils import (
    format_journal_summary,
    format_signal_summary,
    format_trade_details,
)
from system.algo_trader.strategy.journal import TradeJournal
from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy


def create_strategy(args, logger):
    if args.strategy == "sma-crossover":
        logger.info(
            f"Initializing SMA Crossover: short={args.short}, long={args.long}"
        )
        return SMACrossoverStrategy(
            short_window=args.short,
            long_window=args.long,
            database=args.database,
            use_threading=args.threading,
        )
    else:
        raise ValueError(f"Unknown strategy: {args.strategy}")


def run_strategy_for_tickers(strategy, tickers, start_time_str, args, logger):
    if len(tickers) == 1:
        logger.info(f"Running strategy for single ticker: {tickers[0]}")
        return strategy.run_strategy(
            ticker=tickers[0],
            start_time=start_time_str,
            limit=args.limit,
            write_signals=args.write,
        )
    else:
        logger.info(f"Running strategy for {len(tickers)} tickers")
        return strategy.run_strategy_multi(
            tickers=tickers,
            start_time=start_time_str,
            limit=args.limit,
            write_signals=args.write,
        )


def handle_empty_signals(logger):
    logger.warning("No trading signals were generated")
    logger.info("Possible reasons:")
    logger.info("  - Insufficient OHLCV data in InfluxDB")
    logger.info("  - No signal conditions detected in the time range")
    logger.info("  - All signals below min_confidence threshold")
    logger.info("\nTo populate OHLCV data, run:")
    logger.info("  bazel run //system/algo_trader/datasource/populate:main")


def display_signals(signals, args, logger):
    print(format_signal_summary(signals))

    if not args.write:
        logger.info("NOTE: Signals were NOT written to InfluxDB")
        logger.info("To persist signals, run with --write flag")
    else:
        logger.info("Signals have been written to InfluxDB strategy table")


def generate_journal(signals, args, logger, strategy):
    if signals.empty:
        logger.info("Trading Journal: No trades to analyze")
        print("\n" + "=" * 80)
        print("Trading Journal: No signals generated - no trades to analyze")
        print("=" * 80 + "\n")
        return

    logger.info("Generating trading journal...")
    unique_tickers = signals["ticker"].unique()

    for ticker in unique_tickers:
        ticker_signals = signals[signals["ticker"] == ticker]

        # Fetch OHLCV data for efficiency calculation
        ohlcv_data = None
        if not ticker_signals.empty:
            start_time = ticker_signals["signal_time"].min()
            end_time = ticker_signals["signal_time"].max()
            ohlcv_data = strategy.query_ohlcv(
                ticker=ticker,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
            )

        journal = TradeJournal(
            signals=ticker_signals,
            strategy_name=strategy.strategy_name,
            ohlcv_data=ohlcv_data,
            capital_per_trade=args.capital,
            risk_free_rate=args.risk_free_rate,
        )

        metrics, trades = journal.generate_report()
        print(format_journal_summary(metrics, ticker, strategy.strategy_name))

        if args.detailed:
            print(format_trade_details(trades))


def execute_strategy(args, tickers, logger):
    end_time = datetime.now()
    start_time = end_time - timedelta(days=args.lookback)
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Tickers: {len(tickers)} ticker(s)")
    logger.info(f"Time range: {start_time_str} to now ({args.lookback} days)")
    logger.info(f"Threading: {'enabled' if args.threading else 'disabled'}")
    logger.info(f"Database: {args.database}")
    logger.info(f"Write to DB: {args.write}")

    strategy = create_strategy(args, logger)

    try:
        signals = run_strategy_for_tickers(
            strategy, tickers, start_time_str, args, logger
        )

        if signals.empty:
            handle_empty_signals(logger)
        else:
            display_signals(signals, args, logger)

        if args.journal:
            generate_journal(signals, args, logger, strategy)

        return 0
    finally:
        strategy.close()
        logger.info("Strategy execution complete")
