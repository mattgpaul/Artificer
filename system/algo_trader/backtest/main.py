#!/usr/bin/env python3

"""Main entry point for backtesting engine.

This module provides the CLI interface for running backtests on trading strategies.
"""

import argparse
import sys

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.execution import ExecutionConfig
from system.algo_trader.backtest.processor import BacktestProcessor
from system.algo_trader.strategy.cli_utils import resolve_tickers
from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy


def create_strategy(args, logger):
    """Create strategy instance from command-line arguments.

    Args:
        args: Parsed command-line arguments.
        logger: Logger instance.

    Returns:
        Strategy instance.

    Raises:
        ValueError: If strategy type is unknown.
    """
    if args.strategy == "sma-crossover":
        logger.info(f"Initializing SMA Crossover: short={args.short}, long={args.long}")
        return SMACrossoverStrategy(
            short_window=args.short,
            long_window=args.long,
            database=args.database,
            use_threading=False,
        )
    else:
        raise ValueError(f"Unknown strategy: {args.strategy}")


def parse_args():
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Backtesting engine for trading strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        required=True,
        help='Ticker symbols or "full-registry" for all SEC tickers',
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Backtest start date (ISO format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="Backtest end date (ISO format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--database",
        type=str,
        default="algo-trader-ohlcv",
        help="InfluxDB database name for OHLCV data (default: algo-trader-ohlcv)",
    )
    parser.add_argument(
        "--step-frequency",
        type=str,
        default="auto",
        help=(
            "Time-stepping frequency: auto, daily, hourly, minute, or ISO duration (default: auto)"
        ),
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Enable walk-forward analysis",
    )
    parser.add_argument(
        "--train-days",
        type=int,
        default=180,
        help="Training period days for walk-forward (default: 180)",
    )
    parser.add_argument(
        "--test-days",
        type=int,
        default=30,
        help="Testing period days for walk-forward (default: 30)",
    )
    parser.add_argument(
        "--train-split",
        type=float,
        default=None,
        help="Train/test split ratio (0.0-1.0) for simple split",
    )
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=5.0,
        help="Slippage in basis points (default: 5.0)",
    )
    parser.add_argument(
        "--commission",
        type=float,
        default=0.005,
        help="Commission per share (default: 0.005)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Capital per trade (default: 10000)",
    )
    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=0.04,
        help="Risk-free rate for Sharpe ratio (default: 0.04)",
    )
    parser.add_argument(
        "--max-processes",
        type=int,
        default=None,
        help="Maximum number of processes for parallel ticker processing (default: CPU count)",
    )
    parser.add_argument(
        "--no-multiprocessing",
        action="store_true",
        help="Disable multiprocessing and process tickers sequentially (default: False)",
    )

    subparsers = parser.add_subparsers(
        dest="strategy", required=True, help="Trading strategy to backtest"
    )
    sma_parser = subparsers.add_parser(
        "sma-crossover", help="Simple Moving Average crossover strategy"
    )
    SMACrossoverStrategy().add_strategy_arguments(sma_parser)

    return parser.parse_args()


def main():
    """Main entry point for backtesting CLI.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    args = parse_args()
    logger = get_logger("BacktestMain")

    logger.info("=" * 80)
    logger.info("Backtesting Engine")
    logger.info("=" * 80)

    try:
        tickers = resolve_tickers(args.tickers, logger)
    except ValueError as e:
        logger.error(f"Failed to resolve tickers: {e}")
        return 1

    try:
        start_date = pd.Timestamp(args.start_date, tz="UTC")
        end_date = pd.Timestamp(args.end_date, tz="UTC")
    except Exception as e:
        logger.error(f"Invalid date format: {e}")
        return 1

    if start_date >= end_date:
        logger.error("Start date must be before end date")
        return 1

    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Tickers: {len(tickers)} ticker(s)")
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
    logger.info(f"Step frequency: {args.step_frequency}")
    logger.info(f"Database: {args.database}")

    strategy = create_strategy(args, logger)

    execution_config = ExecutionConfig(
        slippage_bps=args.slippage_bps,
        commission_per_share=args.commission,
    )

    strategy_params = {}
    if args.strategy == "sma-crossover":
        strategy_params = {
            "short_window": args.short,
            "long_window": args.long,
        }

    try:
        processor = BacktestProcessor(logger=logger)
        processor.process_tickers(
            strategy=strategy,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            step_frequency=args.step_frequency,
            database=args.database,
            execution_config=execution_config,
            capital_per_trade=args.capital,
            risk_free_rate=args.risk_free_rate,
            strategy_params=strategy_params,
            walk_forward=args.walk_forward,
            train_days=args.train_days if args.walk_forward else None,
            test_days=args.test_days if args.walk_forward else None,
            train_split=args.train_split,
            max_processes=args.max_processes,
            use_multiprocessing=not args.no_multiprocessing,
        )

        return 0

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        return 1
    finally:
        strategy.close()


if __name__ == "__main__":
    sys.exit(main())
