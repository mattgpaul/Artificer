"""Strategy execution orchestration module.

This module provides functions for creating strategies, executing them on tickers,
displaying results, and generating trading journals. It serves as the main
orchestration layer between the CLI (main.py) and strategy implementations.
"""

from datetime import datetime, timedelta

import pandas as pd

from system.algo_trader.strategy.cli_utils import (
    format_group_summary,
    format_journal_summary,
    format_signal_summary,
    format_trade_details,
)
from system.algo_trader.strategy.journal import TradeJournal
from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy


def create_strategy(args, logger):
    """Create and initialize a trading strategy instance from command-line arguments.

    Args:
        args: Parsed command-line arguments containing strategy configuration.
        logger: Logger instance for logging initialization messages.

    Returns:
        Initialized strategy instance (e.g., SMACrossoverStrategy).

    Raises:
        ValueError: If strategy type is unknown or invalid.

    Example:
        >>> args = MagicMock(strategy='sma-crossover', short=10, long=20)
        >>> strategy = create_strategy(args, logger)
        >>> assert isinstance(strategy, SMACrossoverStrategy)
    """
    from infrastructure.config import ThreadConfig  # noqa: PLC0415

    # Create thread config if threading is enabled
    thread_config = None
    if args.threading:
        thread_config = (
            ThreadConfig(max_threads=args.max_threads) if args.max_threads else ThreadConfig()
        )
        logger.info(f"Threading enabled with max_threads={thread_config.max_threads}")

    if args.strategy == "sma-crossover":
        logger.info(f"Initializing SMA Crossover: short={args.short}, long={args.long}")
        return SMACrossoverStrategy(
            short_window=args.short,
            long_window=args.long,
            database=args.database,
            use_threading=args.threading,
            thread_config=thread_config,
        )
    else:
        raise ValueError(f"Unknown strategy: {args.strategy}")


def run_strategy_for_tickers(strategy, tickers, start_time_str, args, logger):
    """Execute strategy for one or more tickers.

    Automatically selects single-ticker or multi-ticker execution based on
    the number of tickers provided.

    Args:
        strategy: Initialized strategy instance to execute.
        tickers: List of ticker symbols to process (single or multiple).
        start_time_str: Start timestamp string for OHLCV data query.
        args: Command-line arguments containing execution parameters.
        logger: Logger instance for logging execution progress.

    Returns:
        DataFrame containing signal summaries for all processed tickers.
        Empty DataFrame if no signals generated.

    Example:
        >>> signals = run_strategy_for_tickers(
        ...     strategy, ['AAPL'], '2024-01-01T00:00:00Z', args, logger
        ... )
    """
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
    """Handle case when no trading signals are generated.

    Logs warning message and provides troubleshooting suggestions for why
    signals might not have been generated.

    Args:
        logger: Logger instance for logging warnings and suggestions.

    Example:
        >>> if signals.empty:
        ...     handle_empty_signals(logger)
    """
    logger.warning("No trading signals were generated")
    logger.info("Possible reasons:")
    logger.info("  - Insufficient OHLCV data in InfluxDB")
    logger.info("  - No signal conditions detected in the time range")
    logger.info("  - All signals below min_confidence threshold")
    logger.info("\nTo populate OHLCV data, run:")
    logger.info("  bazel run //system/algo_trader/datasource/populate:main")


def display_signals(signals, args, logger):
    """Display formatted signal summary to console.

    Formats and prints signal summary, and logs whether signals were
    written to InfluxDB based on args.write flag.

    Args:
        signals: DataFrame containing trading signals to display.
        args: Command-line arguments (used to check write flag).
        logger: Logger instance for logging write status.

    Example:
        >>> display_signals(signals_df, args, logger)
    """
    print(format_signal_summary(signals))

    if not args.write:
        logger.info("NOTE: Signals were NOT written to InfluxDB")
        logger.info("To persist signals, run with --write flag")
    else:
        logger.info("Signals have been written to InfluxDB strategy table")


def generate_journal(signals, args, logger, strategy):
    """Generate and display trading journal for generated signals.

    Creates TradeJournal instances for each ticker, calculates performance
    metrics, and displays formatted summaries. For multiple tickers, also
    generates a group summary across all tickers.

    Args:
        signals: DataFrame containing trading signals to analyze.
        args: Command-line arguments containing journal configuration
            (capital, risk_free_rate, detailed flag).
        logger: Logger instance for logging journal generation progress.
        strategy: Strategy instance used to query OHLCV data for efficiency
            calculations.

    Example:
        >>> generate_journal(signals_df, args, logger, strategy)
    """
    if signals.empty:
        logger.info("Trading Journal: No trades to analyze")
        print("\n" + "=" * 80)
        print("Trading Journal: No signals generated - no trades to analyze")
        print("=" * 80 + "\n")
        return

    logger.info("Generating trading journal...")
    unique_tickers = signals["ticker"].unique()
    all_trades = []

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

        if not trades.empty:
            all_trades.append(trades)

    # Generate group summary if multiple tickers
    if len(unique_tickers) > 1 and all_trades:
        _generate_group_summary(all_trades, args, logger, strategy)


def _generate_group_summary(all_trades, args, logger, strategy):
    """Generate aggregate trading journal summary across multiple tickers.

    Combines trades from all tickers and calculates aggregate performance
    metrics for the entire portfolio.

    Args:
        all_trades: List of DataFrames, each containing trades for one ticker.
        args: Command-line arguments containing journal configuration.
        logger: Logger instance for logging summary generation.
        strategy: Strategy instance (used for strategy_name in formatting).

    Example:
        >>> _generate_group_summary([trades_aapl, trades_msft], args, logger, strategy)
    """
    logger.info("Generating group summary across all tickers...")
    combined_trades = pd.concat(all_trades, ignore_index=True)

    # Create a temporary journal for metrics calculation
    group_journal = TradeJournal(
        signals=pd.DataFrame(),
        strategy_name=strategy.strategy_name,
        capital_per_trade=args.capital,
        risk_free_rate=args.risk_free_rate,
    )

    group_metrics = group_journal.calculate_metrics(combined_trades)
    print(format_group_summary(group_metrics, strategy.strategy_name))

    if args.detailed:
        print(format_trade_details(combined_trades))


def execute_strategy(args, tickers, logger):
    """Execute complete strategy workflow from start to finish.

    Orchestrates the entire strategy execution process:
    1. Creates strategy instance
    2. Calculates time range from lookback period
    3. Executes strategy on tickers
    4. Displays signals or handles empty case
    5. Optionally generates trading journal
    6. Cleans up resources

    Args:
        args: Parsed command-line arguments containing all configuration.
        tickers: List of ticker symbols to process.
        logger: Logger instance for logging execution progress.

    Returns:
        Exit code: 0 for success, non-zero for errors.

    Example:
        >>> exit_code = execute_strategy(args, ['AAPL', 'MSFT'], logger)
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=args.lookback)
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Tickers: {len(tickers)} ticker(s)")
    logger.info(f"Time range: {start_time_str} to now ({args.lookback} days)")
    threading_info = "enabled"
    if args.threading:
        max_threads = args.max_threads if args.max_threads else "default (10 or THREAD_MAX_THREADS)"
        threading_info += f" (max_threads={max_threads})"
    logger.info(f"Threading: {threading_info if args.threading else 'disabled'}")
    logger.info(f"Database: {args.database}")
    logger.info(f"Write to DB: {args.write}")

    strategy = create_strategy(args, logger)

    try:
        signals = run_strategy_for_tickers(strategy, tickers, start_time_str, args, logger)

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
