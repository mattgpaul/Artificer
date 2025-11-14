#!/usr/bin/env python3

import argparse
import sys
from datetime import datetime
from uuid import uuid4

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.engine import BacktestEngine
from system.algo_trader.backtest.execution import ExecutionConfig
from system.algo_trader.backtest.results import ResultsWriter
from system.algo_trader.strategy.cli_utils import resolve_tickers
from system.algo_trader.strategy.sma_crossover import SMACrossoverStrategy


def create_strategy(args, logger):
    from infrastructure.config import ThreadConfig

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


def parse_args():
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
        help="Time-stepping frequency: auto, daily, hourly, minute, or ISO duration (default: auto)",
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
        "--threading",
        action="store_true",
        help="Enable multi-threaded processing (default: False)",
    )
    parser.add_argument(
        "--max-threads",
        type=int,
        default=None,
        help="Maximum number of threads (default: 10 or THREAD_MAX_THREADS env var)",
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

    engine = BacktestEngine(
        strategy=strategy,
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        step_frequency=args.step_frequency,
        database=args.database,
        execution_config=execution_config,
        capital_per_trade=args.capital,
        risk_free_rate=args.risk_free_rate,
    )

    try:
        results = engine.run()

        if results.trades.empty:
            logger.warning("No trades generated during backtest")
            return 0

        backtest_id = str(uuid4())
        results_writer = ResultsWriter()

        success = results_writer.write_trades(
            trades=results.trades,
            strategy_name=results.strategy_name,
            backtest_id=backtest_id,
        )

        if success and results.metrics:
            results_writer.write_metrics(
                metrics=results.metrics,
                strategy_name=results.strategy_name,
                backtest_id=backtest_id,
            )

        results_writer.close()

        print("\n" + "=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)
        print(f"Strategy: {results.strategy_name}")
        print(f"Tickers: {', '.join(tickers)}")
        print(f"Date Range: {start_date.date()} to {end_date.date()}")
        print(f"Total Signals Generated: {len(results.signals)}")
        print(f"\nPerformance Metrics:")
        print(f"  Total Trades: {results.metrics.get('total_trades', 0)}")
        print(f"  Total Profit: ${results.metrics.get('total_profit', 0):.2f}")
        print(f"  Total Profit %: {results.metrics.get('total_profit_pct', 0):.2f}%")
        print(f"  Average Return %: {results.metrics.get('avg_return_pct', 0):.2f}%")
        print(f"  Win Rate: {results.metrics.get('win_rate', 0):.2f}%")
        print(f"  Max Drawdown: {results.metrics.get('max_drawdown', 0):.2f}%")
        print(f"  Sharpe Ratio: {results.metrics.get('sharpe_ratio', 0):.4f}")
        print(f"  Avg Efficiency: {results.metrics.get('avg_efficiency', 0):.1f}%")
        print(f"  Avg Time Held: {results.metrics.get('avg_time_held', 0):.1f} hours")

        if len(results.trades) > 0:
            print(f"\nSample Trades (first 5):")
            sample_trades = results.trades.head(5)
            for idx, trade in sample_trades.iterrows():
                status = "WIN" if trade.get("gross_pnl", 0) > 0 else "LOSS"
                print(
                    f"  {status:4s} | {trade['ticker']:6s} | "
                    f"Entry: ${trade['entry_price']:7.2f} | Exit: ${trade['exit_price']:7.2f} | "
                    f"P&L: ${trade.get('gross_pnl', 0):8.2f} ({trade.get('gross_pnl_pct', 0):6.2f}%)"
                )

        print(f"\nResults written to InfluxDB:")
        print(f"  Database: algo-trader-trading-journal")
        print(f"  Table: {results.strategy_name}")
        print(f"  Backtest ID: {backtest_id}")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        return 1
    finally:
        strategy.close()


if __name__ == "__main__":
    sys.exit(main())

