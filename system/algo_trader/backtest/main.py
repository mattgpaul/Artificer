#!/usr/bin/env python3

"""Main entry point for backtesting engine.

This module provides the CLI interface for running backtests on trading strategies.
"""

import argparse
import inspect
import sys
from typing import Any
from uuid import uuid4

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.cli_utils import resolve_tickers
from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.ohlcv_cache import clear_for_hash
from system.algo_trader.backtest.portfolio_main import run_portfolio_phase
from system.algo_trader.backtest.processor.processor import (
    BacktestProcessor,
    get_backtest_database,
)
from system.algo_trader.backtest.results.hash import compute_backtest_hash
from system.algo_trader.strategy.filters.config_loader import (
    load_filter_config_dicts,
    load_filter_configs,
)
from system.algo_trader.strategy.position_manager.config_loader import (
    load_position_manager_config_dict,
)
from system.algo_trader.strategy.strategy_registry import get_registry


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
    registry = get_registry()
    strategy = registry.create_strategy(args.strategy, args, logger)

    # Log strategy initialization
    strategy_params = {
        "side": getattr(args, "side", "LONG"),
        "window": getattr(args, "window", None),
    }
    # Add strategy-specific parameters
    for attr in dir(args):
        if not attr.startswith("_") and attr not in (
            "strategy",
            "side",
            "window",
            "tickers",
            "start_date",
            "end_date",
            "database",
            "step_frequency",
            "walk_forward",
            "train_days",
            "test_days",
            "train_split",
            "slippage_bps",
            "commission",
            "capital",
            "account_value",
            "trade_percentage",
            "risk_free_rate",
            "max_processes",
            "no_multiprocessing",
            "position_manager",
            "portfolio_manager",
            "filter",
            "lookback_bars",
        ):
            value = getattr(args, attr, None)
            if value is not None:
                strategy_params[attr] = value

    logger.info(
        f"Initializing {args.strategy}: "
        f"{', '.join(f'{k}={v}' for k, v in strategy_params.items() if v is not None)}"
    )

    return strategy


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
        help=(
            'Ticker symbols, "SP500" for S&P 500 tickers, "full-registry" for all SEC tickers, '
            'or "influx-registry" for all tickers in InfluxDB OHLCV database'
        ),
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
        default="ohlcv",
        help="InfluxDB database name for OHLCV data (default: ohlcv)",
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
        "--account-value",
        type=float,
        default=10000.0,
        help="Initial account value for percentage-based position sizing (default: 10000)",
    )
    parser.add_argument(
        "--trade-percentage",
        type=float,
        default=0.10,
        help="Percentage of account value to use per trade (default: 0.10 = 10%%)",
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
    parser.add_argument(
        "--position-manager",
        type=str,
        default=None,
        help=(
            "Name of position manager YAML config under "
            "'system/algo_trader/strategy/position_manager/strategies' "
            "(without .yaml), or an explicit path to a YAML file (optional)"
        ),
    )
    parser.add_argument(
        "--portfolio-manager",
        type=str,
        default=None,
        help=(
            "Name of portfolio manager YAML config under "
            "'system/algo_trader/strategy/portfolio_manager/strategies' "
            "(without .yaml), or an explicit path to a YAML file (optional)"
        ),
    )
    parser.add_argument(
        "--filter",
        type=str,
        action="append",
        default=None,
        help=(
            "Name of filter YAML config under "
            "'system/algo_trader/strategy/filters/strategies' "
            "(without .yaml), or an explicit path to a YAML file. "
            "Can be specified multiple times to combine filters (optional)"
        ),
    )
    parser.add_argument(
        "--lookback-bars",
        type=int,
        default=None,
        help="Maximum number of historical bars to use per time step (default: use all available)",
    )

    subparsers = parser.add_subparsers(
        dest="strategy", required=True, help="Trading strategy to backtest"
    )

    # Auto-register all strategies from the registry
    registry = get_registry()
    registry.register_cli_arguments(subparsers, subparsers.add_parser)

    return parser.parse_args()


def main():  # noqa: C901, PLR0911, PLR0912, PLR0915
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

    position_manager_config_name = args.position_manager
    portfolio_manager_config_name = args.portfolio_manager

    filter_pipeline = load_filter_configs(args.filter, logger)
    filter_config_dict = load_filter_config_dicts(args.filter, logger)

    # Extract strategy parameters dynamically
    strategy_params: dict[str, Any] = {}
    registry = get_registry()
    strategy_class = registry.get_strategy_class(args.strategy)

    if strategy_class:
        # Get strategy-specific parameters by inspecting the constructor
        sig = inspect.signature(strategy_class.__init__)
        for param_name, _param in sig.parameters.items():
            if param_name in ("self", "extra", "_"):
                continue
            if hasattr(args, param_name):
                value = getattr(args, param_name)
                if value is not None:
                    strategy_params[param_name] = value

    try:
        backtest_id = str(uuid4())
        results_database = get_backtest_database()

        logger.info(f"Backtest ID: {backtest_id}")
        logger.info(f"Results Database: {results_database}")

        hash_id = compute_backtest_hash(
            strategy_params=strategy_params,
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency=args.step_frequency,
            database=args.database,
            tickers=tickers,
            capital_per_trade=args.capital,
            risk_free_rate=args.risk_free_rate,
            walk_forward=args.walk_forward,
            train_days=args.train_days if args.walk_forward else None,
            test_days=args.test_days if args.walk_forward else None,
            train_split=args.train_split,
            position_manager_params=load_position_manager_config_dict(
                position_manager_config_name, logger
            ),
            filter_params=filter_config_dict,
        )

        processor = BacktestProcessor(logger=logger)
        processor.process_tickers(
            strategy=strategy,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            step_frequency=args.step_frequency,
            database=args.database,
            results_database=results_database,
            execution_config=execution_config,
            capital_per_trade=args.capital,
            risk_free_rate=args.risk_free_rate,
            strategy_params=strategy_params,
            backtest_id=backtest_id,
            walk_forward=args.walk_forward,
            train_days=args.train_days if args.walk_forward else None,
            test_days=args.test_days if args.walk_forward else None,
            train_split=args.train_split,
            max_processes=args.max_processes,
            use_multiprocessing=not args.no_multiprocessing,
            initial_account_value=args.account_value,
            trade_percentage=args.trade_percentage,
            filter_pipeline=filter_pipeline,
            position_manager_config_name=position_manager_config_name,
            portfolio_manager_config_name=portfolio_manager_config_name,
            filter_config_dict=filter_config_dict,
        )

        if portfolio_manager_config_name:
            logger.info("Starting portfolio manager phase for backtest")
            status = run_portfolio_phase(
                database=results_database,
                hashes=[hash_id],
                portfolio_manager_config=portfolio_manager_config_name,
                initial_account_value=args.account_value,
                ohlcv_database=args.database,
                logger=logger,
            )
            if status != 0:
                logger.error("Portfolio manager phase failed")
                return status

        return 0

    except KeyboardInterrupt:
        logger.info("Backtest interrupted by user")
        if portfolio_manager_config_name:
            try:
                hash_id_local = locals().get("hash_id")
                if hash_id_local:
                    clear_for_hash(hash_id_local)
            except Exception:
                pass
        return 1
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
