"""Results writer for backtest outputs.

This module provides functionality for writing backtest results to Redis queues.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.execution import ExecutionConfig
from system.algo_trader.backtest.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_REDIS_TTL,
    BACKTEST_TRADES_QUEUE_NAME,
    dataframe_to_dict,
)
from system.algo_trader.redis.queue_broker import QueueBroker


class ResultsWriter:
    """Writer for backtest results to Redis queues.

    Args:
        namespace: Redis namespace for queues.
    """

    def __init__(self, namespace: str = "queue") -> None:
        """Initialize results writer.

        Args:
            namespace: Redis namespace for queues.
        """
        self.namespace = namespace
        self.queue_broker = QueueBroker(namespace=namespace)
        self.logger = get_logger(self.__class__.__name__)

    def _compute_backtest_hash(
        self,
        strategy_params: dict[str, Any],
        execution_config: ExecutionConfig,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        step_frequency: str,
        database: str,
        tickers: list[str],
        capital_per_trade: float,
        risk_free_rate: float,
        walk_forward: bool = False,
        train_days: int | None = None,
        test_days: int | None = None,
        train_split: float | None = None,
    ) -> str:
        args_dict = {
            "strategy_params": strategy_params,
            "execution": {
                "slippage_bps": execution_config.slippage_bps,
                "commission_per_share": execution_config.commission_per_share,
                "use_limit_orders": execution_config.use_limit_orders,
                "fill_delay_minutes": execution_config.fill_delay_minutes,
            },
            "backtest": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "step_frequency": step_frequency,
                "database": database,
            },
            "tickers": sorted(tickers),
            "capital_per_trade": capital_per_trade,
            "risk_free_rate": risk_free_rate,
            "walk_forward": walk_forward,
            "train_days": train_days,
            "test_days": test_days,
            "train_split": train_split,
        }
        args_json = json.dumps(args_dict, sort_keys=True, default=str)
        return hashlib.sha256(args_json.encode()).hexdigest()[:16]

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
        """Write trades to Redis queue.

        Args:
            trades: DataFrame containing executed trades.
            strategy_name: Name of the strategy.
            ticker: Ticker symbol.
            backtest_id: Optional backtest identifier.
            strategy_params: Optional strategy parameters.
            execution_config: Optional execution configuration.
            start_date: Optional start date.
            end_date: Optional end date.
            step_frequency: Optional step frequency.
            database: Optional database name.
            tickers: Optional list of tickers.
            capital_per_trade: Optional capital per trade.
            risk_free_rate: Optional risk-free rate.
            walk_forward: Optional walk-forward flag.
            train_days: Optional training days.
            test_days: Optional testing days.
            train_split: Optional train/test split.

        Returns:
            True if successful, False otherwise.
        """
        if trades.empty:
            self.logger.debug(f"No trades to enqueue for {ticker}")
            return True

        backtest_hash = None
        if all(
            [
                strategy_params is not None,
                execution_config is not None,
                start_date is not None,
                end_date is not None,
                step_frequency is not None,
                database is not None,
                tickers is not None,
                capital_per_trade is not None,
                risk_free_rate is not None,
            ]
        ):
            backtest_hash = self._compute_backtest_hash(
                strategy_params=strategy_params,
                execution_config=execution_config,
                start_date=start_date,
                end_date=end_date,
                step_frequency=step_frequency,
                database=database,
                tickers=tickers,
                capital_per_trade=capital_per_trade,
                risk_free_rate=risk_free_rate,
                walk_forward=walk_forward,
                train_days=train_days,
                test_days=test_days,
                train_split=train_split,
            )

        trades_dict = dataframe_to_dict(trades)

        queue_data = {
            "ticker": ticker,
            "strategy_name": strategy_name,
            "backtest_id": backtest_id,
            "backtest_hash": backtest_hash,
            "data": trades_dict,
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
        """Write metrics to Redis queue.

        Args:
            metrics: Dictionary containing performance metrics.
            strategy_name: Name of the strategy.
            ticker: Ticker symbol.
            backtest_id: Optional backtest identifier.
            strategy_params: Optional strategy parameters.
            execution_config: Optional execution configuration.
            start_date: Optional start date.
            end_date: Optional end date.
            step_frequency: Optional step frequency.
            database: Optional database name.
            tickers: Optional list of tickers.
            capital_per_trade: Optional capital per trade.
            risk_free_rate: Optional risk-free rate.
            walk_forward: Optional walk-forward flag.
            train_days: Optional training days.
            test_days: Optional testing days.
            train_split: Optional train/test split.

        Returns:
            True if successful, False otherwise.
        """
        backtest_hash = None
        if all(
            [
                strategy_params is not None,
                execution_config is not None,
                start_date is not None,
                end_date is not None,
                step_frequency is not None,
                database is not None,
                tickers is not None,
                capital_per_trade is not None,
                risk_free_rate is not None,
            ]
        ):
            backtest_hash = self._compute_backtest_hash(
                strategy_params=strategy_params,
                execution_config=execution_config,
                start_date=start_date,
                end_date=end_date,
                step_frequency=step_frequency,
                database=database,
                tickers=tickers,
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
        if backtest_hash:
            metrics_data["backtest_hash"] = [backtest_hash]

        queue_data = {
            "ticker": ticker,
            "strategy_name": strategy_name,
            "backtest_id": backtest_id,
            "backtest_hash": backtest_hash,
            "data": metrics_data,
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
