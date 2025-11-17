"""Results writer for backtest execution.

This module provides functionality to write backtest results (trades and metrics)
to Redis queues for later publication to InfluxDB by the influx-publisher service.
"""

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.results.hash import compute_backtest_hash
from system.algo_trader.backtest.utils.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_REDIS_TTL,
    BACKTEST_TRADES_QUEUE_NAME,
    dataframe_to_dict,
)
from system.algo_trader.redis.queue_broker import QueueBroker


class ResultsWriter:
    """Writes backtest results to Redis queues.

    This class handles writing trades and metrics to Redis queues with proper
    serialization and metadata, including backtest hash computation for deduplication.

    Args:
        namespace: Redis namespace for queue operations. Defaults to "queue".
    """

    def __init__(self, namespace: str = "queue") -> None:
        """Initialize ResultsWriter with Redis namespace.

        Args:
            namespace: Redis namespace for queue operations. Defaults to "queue".
        """
        self.namespace = namespace
        self.queue_broker = QueueBroker(namespace=namespace)
        self.logger = get_logger(self.__class__.__name__)

    def write_trades(
        self,
        trades: pd.DataFrame,
        strategy_name: str,
        ticker: str,
        backtest_id: str | None = None,
        strategy_params: dict[str, Any] | None = None,
        execution_config: ExecutionConfig | None = None,
        start_date: pd.Timestamp | None = None,
        end_date: pd.Timestamp | None = None,
        step_frequency: str | None = None,
        database: str | None = None,
        tickers: list[str] | None = None,
        capital_per_trade: float | None = None,
        risk_free_rate: float | None = None,
        walk_forward: bool = False,
        train_days: int | None = None,
        test_days: int | None = None,
        train_split: float | None = None,
    ) -> bool:
        """Write backtest trades to Redis queue.

        Serializes trades DataFrame and writes to Redis queue with metadata
        including backtest hash for deduplication.

        Args:
            trades: DataFrame containing executed trades.
            strategy_name: Name of the strategy used.
            ticker: Ticker symbol that was backtested.
            backtest_id: Optional unique identifier for this backtest.
            strategy_params: Optional strategy parameters for hash computation.
            execution_config: Optional execution config for hash computation.
            start_date: Optional start date for hash computation.
            end_date: Optional end date for hash computation.
            step_frequency: Optional step frequency for hash computation.
            database: Optional database name for hash computation.
            tickers: Optional ticker list for hash computation.
            capital_per_trade: Optional capital per trade for hash computation.
            risk_free_rate: Optional risk-free rate for hash computation.
            walk_forward: Whether walk-forward analysis was used.
            train_days: Number of training days (if walk-forward).
            test_days: Number of test days (if walk-forward).
            train_split: Training split ratio (if walk-forward).

        Returns:
            True if trades were successfully enqueued, False otherwise.
        """
        if trades.empty:
            self.logger.debug(f"No trades to enqueue for {ticker}")
            return True

        hash_id = None
        if all(
            [
                strategy_params is not None,
                execution_config is not None,
                step_frequency is not None,
                capital_per_trade is not None,
                risk_free_rate is not None,
            ]
        ):
            hash_id = compute_backtest_hash(
                strategy_params=strategy_params,
                execution_config=execution_config,
                start_date=start_date or pd.Timestamp.now(tz="UTC"),
                end_date=end_date or pd.Timestamp.now(tz="UTC"),
                step_frequency=step_frequency,
                database=database or "",
                tickers=tickers or [],
                capital_per_trade=capital_per_trade,
                risk_free_rate=risk_free_rate,
                walk_forward=walk_forward,
                train_days=train_days,
                test_days=test_days,
                train_split=train_split,
            )

        trades_dict = dataframe_to_dict(trades)

        # Log at debug level
        self.logger.debug(f"Writing {len(trades)} trades to Redis for {ticker}")

        queue_data = {
            "ticker": ticker,
            "strategy_name": strategy_name,
            "backtest_id": backtest_id,
            "hash_id": hash_id,
            "strategy_params": strategy_params,  # Include strategy params for tag generation
            "data": trades_dict,
            "database": database,
        }

        item_id = f"{ticker}_{strategy_name}_{backtest_id or 'no_id'}"

        try:
            success = self.queue_broker.enqueue(
                queue_name=BACKTEST_TRADES_QUEUE_NAME,
                item_id=item_id,
                data=queue_data,
                ttl=BACKTEST_REDIS_TTL,
            )

            if success:
                self.logger.debug(
                    f"Enqueued {len(trades)} trades for {ticker} to {BACKTEST_TRADES_QUEUE_NAME}"
                )
                return True
            else:
                self.logger.error(f"Failed to enqueue trades for {ticker} to Redis")
                return False

        except Exception as e:
            self.logger.error(f"Error enqueueing trades for {ticker}: {e}")
            return False

    def write_metrics(
        self,
        metrics: dict,
        strategy_name: str,
        ticker: str,
        backtest_id: str | None = None,
        strategy_params: dict[str, Any] | None = None,
        execution_config: ExecutionConfig | None = None,
        start_date: pd.Timestamp | None = None,
        end_date: pd.Timestamp | None = None,
        step_frequency: str | None = None,
        database: str | None = None,
        tickers: list[str] | None = None,
        capital_per_trade: float | None = None,
        risk_free_rate: float | None = None,
        walk_forward: bool = False,
        train_days: int | None = None,
        test_days: int | None = None,
        train_split: float | None = None,
    ) -> bool:
        """Write backtest metrics to Redis queue.

        Formats performance metrics and writes to Redis queue with metadata
        including backtest hash for deduplication.

        Args:
            metrics: Dictionary containing performance metrics.
            strategy_name: Name of the strategy used.
            ticker: Ticker symbol that was backtested.
            backtest_id: Optional unique identifier for this backtest.
            strategy_params: Optional strategy parameters for hash computation.
            execution_config: Optional execution config for hash computation.
            start_date: Optional start date for hash computation.
            end_date: Optional end date for hash computation.
            step_frequency: Optional step frequency for hash computation.
            database: Optional database name for hash computation.
            tickers: Optional ticker list for hash computation.
            capital_per_trade: Optional capital per trade for hash computation.
            risk_free_rate: Optional risk-free rate for hash computation.
            walk_forward: Whether walk-forward analysis was used.
            train_days: Number of training days (if walk-forward).
            test_days: Number of test days (if walk-forward).
            train_split: Training split ratio (if walk-forward).

        Returns:
            True if metrics were successfully enqueued, False otherwise.
        """
        hash_id = None
        if all(
            [
                strategy_params is not None,
                execution_config is not None,
                step_frequency is not None,
                capital_per_trade is not None,
                risk_free_rate is not None,
            ]
        ):
            hash_id = compute_backtest_hash(
                strategy_params=strategy_params,
                execution_config=execution_config,
                start_date=start_date or pd.Timestamp.now(tz="UTC"),
                end_date=end_date or pd.Timestamp.now(tz="UTC"),
                step_frequency=step_frequency,
                database=database or "",
                tickers=tickers or [],
                capital_per_trade=capital_per_trade,
                risk_free_rate=risk_free_rate,
                walk_forward=walk_forward,
                train_days=train_days,
                test_days=test_days,
                train_split=train_split,
            )

        datetime_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        metrics_data = {
            "datetime": [datetime_ms],
            "total_trades": [metrics.get("total_trades", 0)],
            "total_profit": [round(metrics.get("total_profit", 0), 2)],
            "total_profit_pct": [round(metrics.get("total_profit_pct", 0), 2)],
            "max_drawdown": [round(metrics.get("max_drawdown", 0), 2)],
            "sharpe_ratio": [round(metrics.get("sharpe_ratio", 0), 4)],
            "avg_efficiency": [round(metrics.get("avg_efficiency", 0), 2)],
            "avg_return_pct": [round(metrics.get("avg_return_pct", 0), 2)],
            "avg_time_held": [round(metrics.get("avg_time_held", 0), 2)],
            "win_rate": [round(metrics.get("win_rate", 0), 2)],
            "strategy": [strategy_name],
        }

        if backtest_id:
            metrics_data["backtest_id"] = [backtest_id]
        if hash_id:
            metrics_data["hash_id"] = [hash_id]

        # Log at debug level
        self.logger.debug(f"Writing metrics to Redis for {ticker}")

        queue_data = {
            "ticker": ticker,
            "strategy_name": strategy_name,
            "backtest_id": backtest_id,
            "hash_id": hash_id,
            "data": metrics_data,
            "database": database,
        }

        item_id = f"{ticker}_{strategy_name}_{backtest_id or 'no_id'}_metrics"

        try:
            success = self.queue_broker.enqueue(
                queue_name=BACKTEST_METRICS_QUEUE_NAME,
                item_id=item_id,
                data=queue_data,
                ttl=BACKTEST_REDIS_TTL,
            )

            if success:
                self.logger.debug(f"Enqueued metrics for {ticker} to {BACKTEST_METRICS_QUEUE_NAME}")
                return True
            else:
                self.logger.error(f"Failed to enqueue metrics for {ticker} to Redis")
                return False

        except Exception as e:
            self.logger.error(f"Error enqueueing metrics for {ticker}: {e}")
            return False
