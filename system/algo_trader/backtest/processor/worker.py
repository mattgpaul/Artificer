"""Worker functions for backtest execution.

This module provides worker functions that execute backtests for individual
tickers, including strategy creation, execution, and result writing.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.engine import BacktestEngine, BacktestResults
from system.algo_trader.backtest.results.writer import ResultsWriter
from system.algo_trader.strategy.position_manager.position_manager import (
    PositionManager,
    PositionManagerConfig,
)
from system.algo_trader.strategy.strategies.sma_crossover import SMACrossover
from system.algo_trader.strategy.strategy import Side


def create_strategy_instance(strategy_type: str, strategy_params: dict):
    """Create a strategy instance from type and parameters.

    Args:
        strategy_type: Type of strategy to create (e.g., 'SMACrossover').
        strategy_params: Dictionary of strategy parameters.
            Supports both old parameter names (short_window/long_window) and
            new parameter names (short/long) for backward compatibility.

    Returns:
        Strategy instance of the specified type.

    Raises:
        ValueError: If strategy_type is not recognized.
    """
    if strategy_type == "SMACrossover":
        side_value = strategy_params.get("side", "LONG")
        side = Side(side_value) if isinstance(side_value, str) else side_value
        # Support both old (short_window/long_window) and new (short/long) parameter names
        short = strategy_params.get("short")
        if short is None:
            short = strategy_params.get("short_window", 10)
        long = strategy_params.get("long")
        if long is None:
            long = strategy_params.get("long_window", 20)
        return SMACrossover(
            short=short,
            long=long,
            window=strategy_params.get("window", 120),
            side=side,
        )
    raise ValueError(f"Unknown strategy type: {strategy_type}")


def log_backtest_results(ticker: str, results: "BacktestResults") -> None:
    """Log backtest results to console.

    Args:
        ticker: Ticker symbol that was backtested.
        results: BacktestResults object containing metrics and trades.
    """
    logger = get_logger("BacktestWorker")
    if results.metrics:
        logger.info(
            f"\n{ticker} Backtest Results:\n"
            f"  Strategy: {results.strategy_name}\n"
            f"  Total Trades: {results.metrics.get('total_trades', 0)}\n"
            f"  Total Profit: ${results.metrics.get('total_profit', 0):,.2f} "
            f"({results.metrics.get('total_profit_pct', 0):.2f}%)\n"
            f"  Max Drawdown: {results.metrics.get('max_drawdown', 0):.2f}%\n"
            f"  Sharpe Ratio: {results.metrics.get('sharpe_ratio', 0):.4f}\n"
            f"  Win Rate: {results.metrics.get('win_rate', 0):.2f}%\n"
            f"  Efficiency: {results.metrics.get('avg_efficiency', 0):.2f}%\n"
        )


def write_backtest_results(
    results: "BacktestResults",
    ticker: str,
    backtest_id: str,
    strategy_params: dict,
    execution_config: ExecutionConfig,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    step_frequency: str,
    database: str,
    capital_per_trade: float,
    risk_free_rate: float,
    walk_forward: bool,
    train_days: int | None,
    test_days: int | None,
    train_split: float | None,
) -> bool:
    """Write backtest results to Redis queues.

    Writes trades to Redis queues for later publication to InfluxDB.
    Summary metrics are no longer stored separately - they can be calculated
    from trades in Grafana with filtering capabilities.

    Args:
        results: BacktestResults object containing trades and metrics.
        ticker: Ticker symbol that was backtested.
        backtest_id: Unique identifier for this backtest run.
        strategy_params: Dictionary of strategy parameters.
        execution_config: Execution configuration used.
        start_date: Start date of backtest period.
        end_date: End date of backtest period.
        step_frequency: Frequency used for time steps.
        database: Database name used for data access.
        capital_per_trade: Capital allocated per trade.
        risk_free_rate: Risk-free rate used for Sharpe ratio.
        walk_forward: Whether walk-forward analysis was used.
        train_days: Number of training days (if walk-forward).
        test_days: Number of test days (if walk-forward).
        train_split: Training split ratio (if walk-forward).

    Returns:
        True if trades were successfully enqueued, False otherwise.
    """
    writer = ResultsWriter()
    trades_success = writer.write_trades(
        trades=results.trades,
        strategy_name=results.strategy_name,
        ticker=ticker,
        backtest_id=backtest_id,
        strategy_params=strategy_params,
        execution_config=execution_config,
        start_date=start_date,
        end_date=end_date,
        step_frequency=step_frequency,
        database=database,
        tickers=[ticker],
        capital_per_trade=capital_per_trade,
        risk_free_rate=risk_free_rate,
        walk_forward=walk_forward,
        train_days=train_days,
        test_days=test_days,
        train_split=train_split,
    )

    return trades_success


def backtest_ticker_worker(args: tuple) -> dict:
    """Execute backtest for a single ticker.

    This is the main worker function called by multiprocessing or sequential processing.
    It creates a strategy instance, runs the backtest engine, and writes results.

    Args:
        args: Tuple containing:
            - ticker: Ticker symbol to backtest
            - strategy_type: Type of strategy to use
            - strategy_params_local: Strategy parameters dictionary
            - start_date_local: Start date for backtest
            - end_date_local: End date for backtest
            - step_frequency_local: Frequency for time steps
            - database_local: Database name for OHLCV data access
            - results_database_local: Database name for backtest results
            - execution_config_dict: Execution config as dictionary
            - capital_per_trade_local: Capital per trade
            - risk_free_rate_local: Risk-free rate
            - backtest_id_local: Unique backtest identifier
            - walk_forward_local: Whether using walk-forward analysis
            - train_days_local: Training days (if walk-forward)
            - test_days_local: Test days (if walk-forward)
            - train_split_local: Training split (if walk-forward)

    Returns:
        Dictionary with 'success' boolean and optional 'error' message.
    """
    (
        ticker,
        strategy_type,
        strategy_params_local,
        start_date_local,
        end_date_local,
        step_frequency_local,
        database_local,
        results_database_local,
        execution_config_dict,
        capital_per_trade_local,
        risk_free_rate_local,
        backtest_id_local,
        walk_forward_local,
        train_days_local,
        test_days_local,
        train_split_local,
        initial_account_value_local,
        trade_percentage_local,
        position_manager_config_dict,
    ) = args

    engine = None
    strategy_instance = None
    logger = get_logger("BacktestWorker")

    try:
        logger.debug(f"Starting backtest for {ticker}")

        strategy_instance = create_strategy_instance(strategy_type, strategy_params_local)

        execution_config = ExecutionConfig(
            slippage_bps=execution_config_dict["slippage_bps"],
            commission_per_share=execution_config_dict["commission_per_share"],
        )

        position_manager = None
        if position_manager_config_dict is not None:
            pm_config = PositionManagerConfig.from_dict(position_manager_config_dict)
            position_manager = PositionManager(pm_config, logger)

        engine = BacktestEngine(
            strategy=strategy_instance,
            tickers=[ticker],
            start_date=start_date_local,
            end_date=end_date_local,
            step_frequency=step_frequency_local,
            database=database_local,
            execution_config=execution_config,
            capital_per_trade=capital_per_trade_local,
            risk_free_rate=risk_free_rate_local,
            initial_account_value=initial_account_value_local,
            trade_percentage=trade_percentage_local,
            position_manager=position_manager,
        )

        results = engine.run_ticker(ticker)

        if results.trades.empty:
            logger.debug(f"{ticker}: No trades generated")
            return {"success": True, "trades": 0}

        log_backtest_results(ticker, results)

        trades_success = write_backtest_results(
            results=results,
            ticker=ticker,
            backtest_id=backtest_id_local,
            strategy_params=strategy_params_local,
            execution_config=execution_config,
            start_date=start_date_local,
            end_date=end_date_local,
            step_frequency=step_frequency_local,
            database=results_database_local,
            capital_per_trade=capital_per_trade_local,
            risk_free_rate=risk_free_rate_local,
            walk_forward=walk_forward_local,
            train_days=train_days_local,
            test_days=test_days_local,
            train_split=train_split_local,
        )

        if trades_success:
            logger.debug(f"{ticker}: Successfully enqueued {len(results.trades)} trades to Redis")
            return {"success": True, "trades": len(results.trades)}
        else:
            logger.error(f"{ticker}: Failed to enqueue trades to Redis")
            return {"success": False, "error": "Redis enqueue failed"}

    except Exception as e:
        logger.error(f"{ticker}: Exception during backtest: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if engine is not None:
            try:
                engine.influx_client.close()
            except Exception as e:
                logger.warning(f"{ticker}: Error closing InfluxDB client: {e}")
        if strategy_instance is not None:
            try:
                strategy_instance.close()
            except Exception:
                pass
