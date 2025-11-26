"""Results writer for backtest execution.

This module provides functionality to write backtest results (trades and metrics)
to Redis queues for later publication to InfluxDB by the influx-publisher service.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.results.schema import (
    BacktestMetricsPayload,
    BacktestStudiesPayload,
    BacktestTradesPayload,
    ValidationError,
)
from system.algo_trader.backtest.utils.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_REDIS_TTL,
    BACKTEST_STUDIES_QUEUE_NAME,
    BACKTEST_TRADES_QUEUE_NAME,
    dataframe_to_dict,
)
from system.algo_trader.redis.queue_broker import QueueBroker


def _determine_action(side: str, is_entry: bool) -> str:
    if side == "LONG":
        return "buy_to_open" if is_entry else "sell_to_close"
    else:
        return "sell_to_open" if is_entry else "buy_to_close"


def _compute_execution_id(
    ticker: str,
    strategy: str,
    trade_id: Any,
    timestamp: Any,
    side: str,
    action: str,
    price: float,
    shares: float,
) -> str:
    """Compute a deterministic execution identifier for a single journal row."""
    try:
        ts = pd.to_datetime(timestamp, utc=True)
        ts_str = ts.isoformat()
    except Exception:
        ts_str = str(timestamp)

    trade_id_str = "" if trade_id is None else str(trade_id)
    raw = f"{ticker}|{strategy}|{trade_id_str}|{ts_str}|{side}|{action}|{shares}|{price}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _transform_trades_to_journal_rows(
    trades: pd.DataFrame,
    executions: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Transform trades or execution intents into journal rows.

    Prefer execution-based journaling when we have PM-managed signals; otherwise
    fall back to trade-based journaling.
    """
    if _should_use_execution_journaling(executions):
        exec_df = executions.copy()
        exec_df = exec_df.sort_values(["ticker", "signal_time"])
        return _journal_rows_from_executions(exec_df)

    return _journal_rows_from_trades(trades)


def _should_use_execution_journaling(executions: pd.DataFrame | None) -> bool:
    """Return True if we should use execution-based journaling."""
    if executions is None or executions.empty:
        return False

    columns = executions.columns
    return "action" in columns and "shares" in columns


def _journal_rows_from_executions(exec_df: pd.DataFrame) -> pd.DataFrame:
    """Build journal rows from PM-managed execution intents."""
    journal_rows: list[dict[str, Any]] = []
    trade_ids: dict[str, int] = {}
    position_sizes: dict[str, float] = {}

    for _, row in exec_df.iterrows():
        journal_row = _process_execution_row(row, trade_ids, position_sizes)
        if journal_row is not None:
            journal_rows.append(journal_row)

    if not journal_rows:
        return pd.DataFrame()

    return pd.DataFrame(journal_rows)


def _process_execution_row(
    row: pd.Series,
    trade_ids: dict[str, int],
    position_sizes: dict[str, float],
) -> dict[str, Any] | None:
    """Process a single execution row into a journal row, updating state."""
    ticker = row.get("ticker", "")
    if not ticker:
        return None

    shares = row.get("shares")
    price = row.get("price")
    if _has_missing_price_or_shares(shares, price):
        return None

    try:
        shares_f = float(shares)
        price_f = float(price)
    except (TypeError, ValueError):
        return None

    side = row.get("side", "LONG")
    action = row.get("action")
    ts = row.get("signal_time")
    reason = row.get("reason")

    trade_id = _assign_trade_id_for_execution(
        ticker=ticker,
        action=action,
        side=side,
        shares=shares_f,
        trade_ids=trade_ids,
        position_sizes=position_sizes,
    )
    if trade_id is None:
        # Unknown action type - skip
        return None

    return _build_execution_journal_row(
        row=row,
        side=side,
        price_f=price_f,
        shares_f=shares_f,
        trade_id=trade_id,
        timestamp=ts,
        reason=reason,
    )


def _has_missing_price_or_shares(shares: Any, price: Any) -> bool:
    """Return True if price or shares is missing or NaN."""
    return shares is None or price is None or pd.isna(shares) or pd.isna(price)


def _assign_trade_id_for_execution(
    ticker: str,
    action: Any,
    side: str,
    shares: float,
    trade_ids: dict[str, int],
    position_sizes: dict[str, float],
) -> int | None:
    """Update trade ID and position size state for an execution, returning trade_id.

    Returns None if the action is unknown and the row should be skipped.
    """
    normalized_action: str | None
    if action in {"open", "scale_in", "scale_out", "close"}:
        normalized_action = str(action)
    elif action in {"buy_to_open", "sell_to_open"}:
        normalized_action = "open"
    elif action in {"buy_to_close", "sell_to_close"}:
        normalized_action = "close"
    else:
        return None

    if ticker not in trade_ids:
        trade_ids[ticker] = 0
        position_sizes[ticker] = 0.0

    current_size = position_sizes[ticker]

    if normalized_action in {"close", "scale_out"} and current_size <= 0.0:
        return None

    if normalized_action in {"open", "scale_in"} and current_size <= 0.0:
        trade_ids[ticker] += 1

    trade_id = trade_ids[ticker]

    if normalized_action in {"open", "scale_in"}:
        position_sizes[ticker] = current_size + shares
    elif normalized_action in {"scale_out", "close"}:
        position_sizes[ticker] = max(0.0, current_size - shares)
    else:
        return None

    return trade_id


def _build_execution_journal_row(
    row: pd.Series,
    side: str,
    price_f: float,
    shares_f: float,
    trade_id: int,
    timestamp: Any,
    reason: Any,
) -> dict[str, Any]:
    """Build a single journal row dict from an execution row."""
    ticker = row.get("ticker", "")
    commission = row.get("commission", 0.0)

    raw_action = row.get("action")
    if raw_action in {"open", "scale_in", "scale_out", "close"}:
        is_entry = raw_action in {"open", "scale_in"}
    elif raw_action in {"buy_to_open", "sell_to_open"}:
        is_entry = True
    elif raw_action in {"buy_to_close", "sell_to_close"}:
        is_entry = False
    else:
        return None

    action = _determine_action(side=side, is_entry=is_entry)

    execution_id = _compute_execution_id(
        ticker=ticker,
        strategy=row.get("strategy", ""),
        trade_id=trade_id,
        timestamp=timestamp,
        side=side,
        action=action,
        price=price_f,
        shares=shares_f,
    )

    journal_row: dict[str, Any] = {
        "datetime": timestamp,
        "ticker": ticker,
        "side": side,
        "price": price_f,
        "shares": shares_f,
        "commission": float(commission) if commission is not None else 0.0,
        "action": action,
        "execution": execution_id,
    }

    if trade_id:
        journal_row["trade_id"] = float(trade_id)
    if reason is not None:
        journal_row["exit_reason"] = reason

    return journal_row


def _journal_rows_from_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Build journal rows from legacy trade records."""
    if trades.empty:
        return pd.DataFrame()

    _validate_trade_columns(trades)

    journal_rows: list[dict[str, Any]] = []
    for _, trade in trades.iterrows():
        journal_rows.extend(_journal_rows_for_trade(trade))

    return pd.DataFrame(journal_rows)


def _validate_trade_columns(trades: pd.DataFrame) -> None:
    """Validate that the trades DataFrame has all required columns."""
    required_cols = ["entry_time", "exit_time", "entry_price", "exit_price", "shares"]
    missing_cols = [col for col in required_cols if col not in trades.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in trades DataFrame: {missing_cols}")


def _journal_rows_for_trade(trade: pd.Series) -> list[dict[str, Any]]:
    """Return entry and exit journal rows for a single trade."""
    side = trade.get("side", "LONG")
    ticker = trade.get("ticker", "")
    strategy = trade.get("strategy", "")
    trade_id = trade.get("trade_id")
    commission = trade.get("commission", 0.0)

    entry_action = _determine_action(side, True)
    exit_action = _determine_action(side, False)

    entry_execution = _compute_execution_id(
        ticker=ticker,
        strategy=strategy,
        trade_id=trade_id,
        timestamp=trade["entry_time"],
        side=side,
        action=entry_action,
        price=float(trade["entry_price"]),
        shares=float(trade["shares"]),
    )

    exit_execution = _compute_execution_id(
        ticker=ticker,
        strategy=strategy,
        trade_id=trade_id,
        timestamp=trade["exit_time"],
        side=side,
        action=exit_action,
        price=float(trade["exit_price"]),
        shares=float(trade["shares"]),
    )

    entry_row: dict[str, Any] = {
        "datetime": trade["entry_time"],
        "ticker": ticker,
        "side": side,
        "price": trade["entry_price"],
        "shares": trade["shares"],
        "commission": commission,
        "action": entry_action,
        "execution": entry_execution,
    }
    if trade_id is not None:
        entry_row["trade_id"] = trade_id

    exit_row: dict[str, Any] = {
        "datetime": trade["exit_time"],
        "ticker": ticker,
        "side": side,
        "price": trade["exit_price"],
        "shares": trade["shares"],
        "commission": commission,
        "action": exit_action,
        "execution": exit_execution,
    }
    if trade_id is not None:
        exit_row["trade_id"] = trade_id

    return [entry_row, exit_row]


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
        filter_params: dict[str, Any] | None = None,
        hash_id: str | None = None,
        portfolio_stage: str = "final",
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
            filter_params: Optional dictionary containing filter configuration
                for hash computation. If None, filters are not included in hash.
            hash_id: Optional canonical hash ID for this backtest configuration.
                If None, hash will be computed from other parameters.

        Returns:
            True if trades were successfully enqueued, False otherwise.
        """
        if trades.empty:
            self.logger.debug(f"No trades to enqueue for {ticker}")
            return True

        # Prefer using PM-managed execution intents when present on the trades
        executions = None
        if "action" in trades.columns and "shares" in trades.columns:
            executions = trades

        journal_rows = _transform_trades_to_journal_rows(trades, executions=executions)
        trades_dict = dataframe_to_dict(journal_rows)

        row_count = len(journal_rows)
        self.logger.debug(
            f"Writing {row_count} journal rows ({len(trades)} trades) to Redis for {ticker}"
        )

        # Validate payload structure with Pydantic before enqueueing.
        try:
            payload = BacktestTradesPayload(
                ticker=ticker,
                strategy_name=strategy_name,
                backtest_id=backtest_id,
                hash_id=hash_id,
                strategy_params=strategy_params,
                data=trades_dict,
                database=database,
                portfolio_stage=portfolio_stage,
            )
        except ValidationError as e:
            self.logger.error(
                "Validation error building backtest trades payload for "
                f"{ticker} / {strategy_name}: {e}"
            )
            return False

        queue_data = payload.model_dump()

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
                    f"Enqueued {row_count} journal rows ({len(trades)} trades) for {ticker} "
                    f"to {BACKTEST_TRADES_QUEUE_NAME}"
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
        filter_params: dict[str, Any] | None = None,
        hash_id: str | None = None,
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
            filter_params: Optional dictionary containing filter configuration
                for hash computation. If None, filters are not included in hash.
            hash_id: Optional canonical hash ID for this backtest configuration.
                If None, hash will be computed from other parameters.

        Returns:
            True if metrics were successfully enqueued, False otherwise.
        """
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

        # Validate payload structure with Pydantic before enqueueing.
        try:
            payload = BacktestMetricsPayload(
                ticker=ticker,
                strategy_name=strategy_name,
                backtest_id=backtest_id,
                hash_id=hash_id,
                data=metrics_data,
                database=database,
            )
        except ValidationError as e:
            self.logger.error(
                "Validation error building backtest metrics payload for "
                f"{ticker} / {strategy_name}: {e}"
            )
            return False

        queue_data = payload.model_dump()

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

    def write_studies(
        self,
        studies: pd.DataFrame,
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
        filter_params: dict[str, Any] | None = None,
        hash_id: str | None = None,
    ) -> bool:
        """Write study results to Redis queue for InfluxDB publication.

        Enqueues study data (technical indicators) to Redis for later batch
        publication to InfluxDB. Studies are written with metadata including
        strategy parameters, execution config, and backtest context.

        Args:
            studies: DataFrame containing study results to enqueue.
            strategy_name: Name of the strategy that generated the studies.
            ticker: Ticker symbol for the studies.
            backtest_id: Unique identifier for this backtest run.
            strategy_params: Dictionary of strategy parameters.
            execution_config: Execution configuration used.
            start_date: Start date of backtest period.
            end_date: End date of backtest period.
            step_frequency: Frequency used for time steps.
            database: Database name used for data access.
            tickers: List of tickers in the backtest.
            capital_per_trade: Capital allocated per trade.
            risk_free_rate: Risk-free rate used for Sharpe ratio.
            walk_forward: Whether walk-forward analysis was used.
            train_days: Number of training days (if walk-forward).
            test_days: Number of test days (if walk-forward).
            train_split: Training split ratio (if walk-forward).
            filter_params: Optional dictionary containing filter configuration
                for hash computation. If None, filters are not included in hash.
            hash_id: Optional canonical hash ID for this backtest configuration.
                If None, hash will be computed from other parameters.

        Returns:
            True if studies were successfully enqueued, False otherwise.
        """
        if studies.empty:
            self.logger.debug(f"No studies to enqueue for {ticker}")
            return True

        self.logger.debug(
            f"Preparing studies for {ticker}: rows={len(studies)}, columns={list(studies.columns)}"
        )
        try:
            non_null_counts = studies.count().to_dict()
            self.logger.debug(f"Non-null study counts for {ticker}: {non_null_counts}")
        except Exception:
            # Defensive: avoid breaking writes due to logging issues
            pass

        studies_dict = dataframe_to_dict(studies)

        row_count = len(studies)
        self.logger.debug(f"Writing {row_count} study rows to Redis for {ticker}")

        try:
            payload = BacktestStudiesPayload(
                ticker=ticker,
                strategy_name=strategy_name,
                backtest_id=backtest_id,
                hash_id=hash_id,
                strategy_params=strategy_params,
                data=studies_dict,
                database=database,
            )
        except ValidationError as e:
            self.logger.error(
                "Validation error building backtest studies payload for "
                f"{ticker} / {strategy_name}: {e}"
            )
            return False

        queue_data = payload.model_dump()

        item_id = f"{ticker}_{strategy_name}_{backtest_id or 'no_id'}_studies"

        try:
            success = self.queue_broker.enqueue(
                queue_name=BACKTEST_STUDIES_QUEUE_NAME,
                item_id=item_id,
                data=queue_data,
                ttl=BACKTEST_REDIS_TTL,
            )

            if success:
                self.logger.debug(
                    f"Enqueued {row_count} study rows for {ticker} to {BACKTEST_STUDIES_QUEUE_NAME}"
                )
                return True
            else:
                self.logger.error(f"Failed to enqueue studies for {ticker} to Redis")
                return False

        except Exception as e:
            self.logger.error(f"Error enqueueing studies for {ticker}: {e}")
            return False
