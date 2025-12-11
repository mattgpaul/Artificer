"""Unit and integration tests for ResultsWriter.

Tests cover initialization, trade/metrics writing, backtest hash computation,
DataFrame conversion, Redis operations, and complete workflows. All external
dependencies are mocked via conftest.py. Integration tests use 'debug' database.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.results.hash import compute_backtest_hash
from system.algo_trader.backtest.results.writer import (
    ResultsWriter,
    _compute_execution_id,
)
from system.algo_trader.backtest.utils.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_REDIS_TTL,
    BACKTEST_STUDIES_QUEUE_NAME,
    BACKTEST_TRADES_QUEUE_NAME,
)

# Import helper function from conftest
from tests.system.algo_trader.backtest.results.conftest import assert_execution_field


class TestComputeExecutionId:
    """Test _compute_execution_id function."""

    @pytest.mark.unit
    def test_execution_id_deterministic(self, base_execution_params):
        """Test execution ID is deterministic for same inputs."""
        exec_id_1 = _compute_execution_id(**base_execution_params)
        exec_id_2 = _compute_execution_id(**base_execution_params)

        assert exec_id_1 == exec_id_2
        assert len(exec_id_1) == 16  # 16 hex characters

    @pytest.mark.unit
    def test_execution_id_different_for_different_inputs(self, base_execution_params):
        """Test execution ID differs for different inputs."""
        exec_id_base = _compute_execution_id(**base_execution_params)

        # Different ticker
        exec_id_ticker = _compute_execution_id(**{**base_execution_params, "ticker": "MSFT"})
        assert exec_id_base != exec_id_ticker

        # Different price
        exec_id_price = _compute_execution_id(**{**base_execution_params, "price": 101.0})
        assert exec_id_base != exec_id_price

        # Different shares
        exec_id_shares = _compute_execution_id(**{**base_execution_params, "shares": 200.0})
        assert exec_id_base != exec_id_shares

        # Different action
        exec_id_action = _compute_execution_id(
            **{**base_execution_params, "action": "sell_to_close"}
        )
        assert exec_id_base != exec_id_action

        # Different timestamp
        exec_id_time = _compute_execution_id(
            **{**base_execution_params, "timestamp": pd.Timestamp("2024-01-06", tz="UTC")}
        )
        assert exec_id_base != exec_id_time

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "trade_id,expected_empty",
        [
            (None, True),
            (1, False),
            (0, False),
            ("", True),
        ],
    )
    def test_execution_id_handles_none_trade_id(
        self, base_execution_params, trade_id, expected_empty
    ):
        """Test execution ID handles None/empty trade_id correctly."""
        exec_id = _compute_execution_id(**{**base_execution_params, "trade_id": trade_id})

        assert len(exec_id) == 16
        # Should still produce valid hash even with None trade_id
        assert isinstance(exec_id, str)

    @pytest.mark.unit
    def test_execution_id_handles_invalid_timestamp(self, base_execution_params):
        """Test execution ID handles invalid timestamp gracefully."""
        exec_id = _compute_execution_id(
            **{**base_execution_params, "timestamp": "invalid-timestamp"}
        )

        assert len(exec_id) == 16
        assert isinstance(exec_id, str)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "side,action,expected_action",
        [
            ("LONG", "buy_to_open", "buy_to_open"),
            ("LONG", "sell_to_close", "sell_to_close"),
            ("SHORT", "sell_to_open", "sell_to_open"),
            ("SHORT", "buy_to_close", "buy_to_close"),
        ],
    )
    def test_execution_id_different_for_different_sides_and_actions(
        self, base_execution_params, side, action, expected_action
    ):
        """Test execution ID differs for different sides and actions."""
        exec_id_1 = _compute_execution_id(
            **{**base_execution_params, "side": side, "action": action}
        )
        exec_id_2 = _compute_execution_id(
            **{**base_execution_params, "side": "LONG", "action": "buy_to_open"}
        )

        if side != "LONG" or action != "buy_to_open":
            assert exec_id_1 != exec_id_2


class TestResultsWriterInitialization:
    """Test ResultsWriter initialization."""

    @pytest.mark.unit
    def test_initialization_default_namespace(self, mock_queue_broker):
        """Test initialization with default namespace."""
        writer = ResultsWriter()
        assert writer.namespace == "queue"
        assert writer.queue_broker is not None

    @pytest.mark.unit
    def test_initialization_custom_namespace(self, mock_queue_broker):
        """Test initialization with custom namespace."""
        writer = ResultsWriter(namespace="custom")
        assert writer.namespace == "custom"

    @pytest.mark.unit
    def test_initialization_creates_queue_broker(self, mock_queue_broker):
        """Test initialization creates QueueBroker."""
        with patch("system.algo_trader.backtest.results.writer.QueueBroker") as mock_broker_class:
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker

            writer = ResultsWriter()

            assert writer.queue_broker == mock_broker
            mock_broker_class.assert_called_once_with(namespace="queue")


class TestResultsWriterWriteTrades:
    """Test write_trades method."""

    @pytest.mark.unit
    def test_write_trades_empty(self, results_writer, mock_queue_broker):
        """Test writing empty trades DataFrame."""
        writer = results_writer

        result = writer.write_trades(
            trades=pd.DataFrame(),
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        mock_queue_broker.enqueue.assert_not_called()

    @pytest.mark.unit
    def test_write_trades_success(self, results_writer, mock_queue_broker, sample_trade_single):
        """Test writing trades successfully."""
        writer = results_writer

        trades = sample_trade_single

        execution_config = ExecutionConfig()
        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={"short_window": 10},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert result is True
        mock_queue_broker.enqueue.assert_called_once()
        call_args = mock_queue_broker.enqueue.call_args
        assert call_args[1]["queue_name"] == BACKTEST_TRADES_QUEUE_NAME
        assert call_args[1]["ttl"] == BACKTEST_REDIS_TTL
        assert "hash_id" in call_args[1]["data"]

    @pytest.mark.unit
    def test_write_trades_with_hash(
        self,
        results_writer,
        mock_queue_broker,
        standard_backtest_params,
        standard_backtest_hash_id,
        sample_trade_single,
    ):
        """Test writing trades with backtest hash computation."""
        writer = results_writer

        trades = sample_trade_single

        # Update strategy_params for this specific test
        strategy_params = {"short_window": 10, "long_window": 20}
        hash_id = compute_backtest_hash(
            strategy_params=strategy_params,
            execution_config=standard_backtest_params["execution_config"],
            start_date=standard_backtest_params["start_date"],
            end_date=standard_backtest_params["end_date"],
            step_frequency=standard_backtest_params["step_frequency"],
            database="debug",
            tickers=standard_backtest_params["tickers"],
            capital_per_trade=standard_backtest_params["capital_per_trade"],
            risk_free_rate=standard_backtest_params["risk_free_rate"],
            walk_forward=standard_backtest_params["walk_forward"],
            train_days=standard_backtest_params["train_days"],
            test_days=standard_backtest_params["test_days"],
            train_split=standard_backtest_params["train_split"],
            filter_params=standard_backtest_params["filter_params"],
        )

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params=strategy_params,
            execution_config=standard_backtest_params["execution_config"],
            start_date=standard_backtest_params["start_date"],
            end_date=standard_backtest_params["end_date"],
            step_frequency=standard_backtest_params["step_frequency"],
            database="debug",
            tickers=standard_backtest_params["tickers"],
            capital_per_trade=standard_backtest_params["capital_per_trade"],
            risk_free_rate=standard_backtest_params["risk_free_rate"],
            hash_id=hash_id,
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["hash_id"] == hash_id
        assert len(queue_data["hash_id"]) == 16  # 16-char hex hash

    @pytest.mark.unit
    def test_write_trades_without_hash_params(
        self, results_writer, mock_queue_broker, sample_trade_single
    ):
        """Test writing trades without hash computation parameters."""
        writer = results_writer

        trades = sample_trade_single

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["hash_id"] is None

    @pytest.mark.unit
    def test_write_trades_failure(self, results_writer, mock_queue_broker, sample_trade_single):
        """Test writing trades failure."""
        writer = results_writer
        mock_queue_broker.enqueue.return_value = False

        trades = sample_trade_single

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_trades_exception(self, results_writer, mock_queue_broker, sample_trade_single):
        """Test writing trades exception handling."""
        writer = results_writer
        mock_queue_broker.enqueue.side_effect = Exception("Redis error")

        trades = sample_trade_single

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_trades_walk_forward_hash(
        self,
        results_writer,
        mock_queue_broker,
        walk_forward_backtest_params,
        walk_forward_backtest_hash_id,
        sample_trade_single,
    ):
        """Test hash computation includes walk-forward parameters."""
        writer = results_writer

        trades = sample_trade_single

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params=walk_forward_backtest_params["strategy_params"],
            execution_config=walk_forward_backtest_params["execution_config"],
            start_date=walk_forward_backtest_params["start_date"],
            end_date=walk_forward_backtest_params["end_date"],
            step_frequency=walk_forward_backtest_params["step_frequency"],
            database=walk_forward_backtest_params["database"],
            tickers=walk_forward_backtest_params["tickers"],
            capital_per_trade=walk_forward_backtest_params["capital_per_trade"],
            risk_free_rate=walk_forward_backtest_params["risk_free_rate"],
            walk_forward=walk_forward_backtest_params["walk_forward"],
            train_days=walk_forward_backtest_params["train_days"],
            test_days=walk_forward_backtest_params["test_days"],
            train_split=walk_forward_backtest_params["train_split"],
            hash_id=walk_forward_backtest_hash_id,
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["hash_id"] == walk_forward_backtest_hash_id

    @pytest.mark.unit
    def test_write_trades_dataframe_conversion(
        self, results_writer, mock_queue_broker, sample_trade_single
    ):
        """Test DataFrame to dict conversion."""
        writer = results_writer

        trades = sample_trade_single

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert "data" in queue_data
        assert "datetime" in queue_data["data"]
        assert isinstance(queue_data["data"]["datetime"], list)
        # Each trade becomes 2 journal rows (entry + exit)
        assert len(queue_data["data"]["datetime"]) == 2
        # Verify execution field is present
        assert_execution_field(queue_data, expected_count=2)

    @pytest.mark.unit
    def test_write_trades_nan_handling(
        self, results_writer, mock_queue_broker, sample_trade_with_nan
    ):
        """Test NaN handling in DataFrame conversion."""
        writer = results_writer

        trades = sample_trade_with_nan

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        # NaN should be handled (converted to 0 or empty string)
        assert "data" in queue_data

    @pytest.mark.unit
    def test_write_trades_all_nan_column(self, results_writer, sample_trade_with_nan):
        """Test handling of all-NaN columns."""
        writer = results_writer

        # Add all_nan_col to the fixture
        trades = sample_trade_with_nan.copy()
        trades["all_nan_col"] = [None]

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        # All-NaN column should be dropped

    @pytest.mark.unit
    def test_write_trades_schema_validation_failure_mismatched_lengths(
        self, results_writer, mock_queue_broker, sample_trade_single
    ):
        """Test that schema validation failure prevents enqueue."""
        writer = results_writer

        trades = sample_trade_single

        # Force an invalid time-series payload with mismatched column lengths.
        with patch(
            "system.algo_trader.backtest.results.writer.dataframe_to_dict"
        ) as mock_df_to_dict:
            mock_df_to_dict.return_value = {
                "datetime": [1704067200000, 1704153600000],  # two timestamps
                "price": [100.0],  # only one price -> length mismatch
            }

            result = writer.write_trades(
                trades=trades,
                strategy_name="TestStrategy",
                ticker="AAPL",
            )

        assert result is False
        mock_queue_broker.enqueue.assert_not_called()

    @pytest.mark.unit
    def test_write_trades_schema_validation_failure_invalid_strategy_params(
        self, results_writer, mock_queue_broker, sample_trade_single
    ):
        """Test that invalid strategy_params keys cause validation failure."""
        writer = results_writer

        trades = sample_trade_single

        # strategy_params with an empty key should fail BacktestTradesPayload validation.
        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            strategy_params={"": 10},
        )

        assert result is False
        mock_queue_broker.enqueue.assert_not_called()

    @pytest.mark.integration
    def test_write_trades_complete_workflow(
        self, results_writer, mock_queue_broker, sample_trades_multiple
    ):
        """Test complete workflow: DataFrame → dict → Redis."""
        writer = results_writer

        trades = sample_trades_multiple

        execution_config = ExecutionConfig()
        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={"short_window": 10},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        assert call_args[1]["queue_name"] == BACKTEST_TRADES_QUEUE_NAME
        assert call_args[1]["item_id"] == "AAPL_TestStrategy_test-id"
        queue_data = call_args[1]["data"]
        assert queue_data["ticker"] == "AAPL"
        assert queue_data["strategy_name"] == "TestStrategy"
        assert queue_data["backtest_id"] == "test-id"
        assert queue_data["database"] == "debug"
        assert queue_data["strategy_params"] == {"short_window": 10}
        # Each trade becomes 2 journal rows (entry + exit), so 2 trades = 4 rows
        assert len(queue_data["data"]["datetime"]) == 4
        # Verify execution field is present
        assert_execution_field(queue_data, expected_count=4)


class TestResultsWriterWriteMetrics:
    """Test write_metrics method."""

    @pytest.mark.unit
    def test_write_metrics_success(self, results_writer, mock_queue_broker):
        """Test writing metrics successfully."""
        writer = results_writer

        metrics = {
            "total_trades": 10,
            "total_profit": 5000.0,
            "total_profit_pct": 50.0,
            "max_drawdown": 5.0,
            "sharpe_ratio": 1.5,
            "avg_efficiency": 75.0,
            "avg_return_pct": 5.0,
            "avg_time_held": 24.0,
            "win_rate": 60.0,
        }

        execution_config = ExecutionConfig()
        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={"short_window": 10},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert result is True
        mock_queue_broker.enqueue.assert_called_once()
        call_args = mock_queue_broker.enqueue.call_args
        assert call_args[1]["queue_name"] == BACKTEST_METRICS_QUEUE_NAME
        assert call_args[1]["ttl"] == BACKTEST_REDIS_TTL

    @pytest.mark.unit
    def test_write_metrics_with_hash(
        self, results_writer, mock_queue_broker, standard_backtest_params, standard_backtest_hash_id
    ):
        """Test writing metrics with hash computation."""
        writer = results_writer

        metrics = {"total_trades": 5}

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params=standard_backtest_params["strategy_params"],
            execution_config=standard_backtest_params["execution_config"],
            start_date=standard_backtest_params["start_date"],
            end_date=standard_backtest_params["end_date"],
            step_frequency=standard_backtest_params["step_frequency"],
            database="debug",
            tickers=standard_backtest_params["tickers"],
            capital_per_trade=standard_backtest_params["capital_per_trade"],
            risk_free_rate=standard_backtest_params["risk_free_rate"],
            hash_id=standard_backtest_hash_id,
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["hash_id"] == standard_backtest_hash_id

    @pytest.mark.unit
    def test_write_metrics_failure(self, results_writer, mock_queue_broker):
        """Test writing metrics failure."""
        writer = results_writer
        mock_queue_broker.enqueue.return_value = False

        metrics = {"total_trades": 5}

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_metrics_schema_validation_failure_invalid_ticker(
        self, results_writer, mock_queue_broker
    ):
        """Test that invalid ticker causes metrics payload validation failure."""
        writer = results_writer

        # Minimal metrics dictionary; hashing will be skipped.
        metrics = {"total_trades": 1}

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="",  # invalid (empty) ticker
        )

        assert result is False
        mock_queue_broker.enqueue.assert_not_called()

    @pytest.mark.unit
    def test_write_metrics_exception(self, results_writer, mock_queue_broker):
        """Test writing metrics exception handling."""
        writer = results_writer
        mock_queue_broker.enqueue.side_effect = Exception("Redis error")

        metrics = {"total_trades": 5}

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_metrics_rounding(self, results_writer, mock_queue_broker):
        """Test metrics values are properly rounded."""
        writer = results_writer

        metrics = {
            "total_profit": 1234.56789,
            "total_profit_pct": 12.3456789,
            "max_drawdown": 5.123456,
            "sharpe_ratio": 1.234567,
            "avg_efficiency": 75.123456,
        }

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        metrics_data = queue_data["data"]
        assert metrics_data["total_profit"][0] == 1234.57  # Rounded to 2 decimals
        assert metrics_data["total_profit_pct"][0] == 12.35
        assert metrics_data["sharpe_ratio"][0] == 1.2346  # Rounded to 4 decimals


class TestResultsWriterHashComputation:
    """Test backtest hash computation."""

    @pytest.mark.unit
    def test_hash_deterministic(self):
        """Test hash is deterministic for same inputs."""
        execution_config = ExecutionConfig(slippage_bps=5.0, commission_per_share=0.005)
        strategy_params = {"short_window": 10, "long_window": 20}

        hash1 = compute_backtest_hash(
            strategy_params=strategy_params,
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        hash2 = compute_backtest_hash(
            strategy_params=strategy_params,
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert hash1 == hash2
        assert len(hash1) == 16

    @pytest.mark.unit
    def test_hash_different_for_different_params(self):
        """Test hash differs for different parameters."""
        execution_config = ExecutionConfig(slippage_bps=5.0, commission_per_share=0.005)

        hash1 = compute_backtest_hash(
            strategy_params={"short_window": 10, "long_window": 20},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        hash2 = compute_backtest_hash(
            strategy_params={"short_window": 20, "long_window": 30},  # Different params
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert hash1 != hash2

    @pytest.mark.unit
    def test_hash_includes_walk_forward(self):
        """Test hash includes walk-forward parameters."""
        execution_config = ExecutionConfig()

        hash1 = compute_backtest_hash(
            strategy_params={},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            walk_forward=False,
        )

        hash2 = compute_backtest_hash(
            strategy_params={},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            walk_forward=True,
            train_days=90,
            test_days=30,
        )

        assert hash1 != hash2

    @pytest.mark.unit
    def test_hash_sorts_tickers(self):
        """Test hash is same regardless of ticker order."""
        execution_config = ExecutionConfig()

        hash1 = compute_backtest_hash(
            strategy_params={},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL", "MSFT"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        hash2 = compute_backtest_hash(
            strategy_params={},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["MSFT", "AAPL"],  # Different order
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert hash1 == hash2  # Should be same due to sorting


class TestResultsWriterDataFrameConversion:
    """Test DataFrame to dict conversion."""

    @pytest.mark.unit
    def test_dataframe_to_dict_datetime_index(self, results_writer, mock_queue_broker):
        """Test conversion with DatetimeIndex."""
        writer = results_writer

        dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"] * 5,
                "entry_time": dates,
                "exit_time": dates + pd.Timedelta(days=1),
                "entry_price": [100.0] * 5,
                "exit_price": [105.0] * 5,
                "shares": [100.0] * 5,
                "gross_pnl": [500.0] * 5,
            },
            index=dates,
        )

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert "datetime" in queue_data["data"]
        # Each trade becomes 2 journal rows (entry + exit), so 5 trades = 10 rows
        assert len(queue_data["data"]["datetime"]) == 10
        # Verify execution field is present
        assert_execution_field(queue_data, expected_count=10)

    @pytest.mark.unit
    def test_dataframe_to_dict_datetime_column(self, results_writer, mock_queue_broker):
        """Test conversion with datetime column."""
        writer = results_writer

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"] * 3,
                "entry_time": pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC"),
                "exit_time": pd.date_range("2024-01-02", periods=3, freq="D", tz="UTC"),
                "entry_price": [100.0] * 3,
                "exit_price": [105.0] * 3,
                "shares": [100.0] * 3,
                "gross_pnl": [500.0] * 3,
            }
        )

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert "datetime" in queue_data["data"]
        assert "datetime" not in queue_data["data"] or queue_data["data"]["datetime"] is not None

    @pytest.mark.unit
    def test_dataframe_to_dict_exit_time_column(
        self, results_writer, mock_queue_broker, sample_trade_single
    ):
        """Test conversion with exit_time column."""
        writer = results_writer

        trades = sample_trade_single

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert "datetime" in queue_data["data"]

    @pytest.mark.unit
    def test_dataframe_to_dict_nan_string_columns(self, results_writer):
        """Test NaN handling in string columns."""
        writer = results_writer

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "shares": [100.0],
                "gross_pnl": [500.0],
                "optional_str": [None],  # NaN string column
            }
        )

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        # NaN should be converted to empty string

    @pytest.mark.unit
    def test_dataframe_to_dict_nan_numeric_columns(self, results_writer):
        """Test NaN handling in numeric columns."""
        writer = results_writer

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "shares": [100.0],
                "gross_pnl": [500.0],
                "optional_num": [None],  # NaN numeric column
            }
        )

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        # NaN should be converted to 0

    @pytest.mark.unit
    def test_dataframe_to_dict_datetime_columns(
        self, results_writer, mock_queue_broker, sample_trade_single
    ):
        """Test datetime column conversion."""
        writer = results_writer

        trades = sample_trade_single

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        # Journal rows have datetime column (not entry_time/exit_time)
        assert "datetime" in queue_data["data"]
        assert isinstance(queue_data["data"]["datetime"], list)
        assert isinstance(queue_data["data"]["datetime"][0], int)
        # Journal rows have price column (not entry_price/exit_price)
        assert "price" in queue_data["data"]
        assert isinstance(queue_data["data"]["price"], list)

    @pytest.mark.integration
    def test_dataframe_to_dict_complete_conversion(
        self, results_writer, mock_queue_broker, sample_trades_multiple
    ):
        """Test complete DataFrame conversion workflow."""
        writer = results_writer

        trades = sample_trades_multiple.copy()
        trades["side"] = ["LONG", "LONG"]
        trades["efficiency"] = [75.5, 80.0]

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        data_dict = queue_data["data"]
        # Each trade becomes 2 journal rows (entry + exit), so 2 trades = 4 rows
        assert len(data_dict["datetime"]) == 4
        assert len(data_dict["ticker"]) == 4
        # Note: gross_pnl may not be in journal rows, check for price instead
        assert "price" in data_dict
        assert len(data_dict["price"]) == 4
        # Verify execution field is present
        assert_execution_field(queue_data, expected_count=4)

    @pytest.mark.unit
    def test_write_trades_pm_managed_executions(
        self, results_writer, mock_queue_broker, sample_pm_executions_open_tp_close
    ):
        """Test execution-based journaling for PM-managed signals with actions/shares."""
        writer = results_writer

        # Simulate PM-managed executions: open, partial TP, final close
        executions = sample_pm_executions_open_tp_close

        result = writer.write_trades(
            trades=executions,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        data = queue_data["data"]

        # One journal row per execution
        assert len(data["datetime"]) == 3
        assert len(data["shares"]) == 3
        assert len(data["action"]) == 3

        # Actions should be mapped to buy_to_open / sell_to_close correctly
        assert data["action"][0] == "buy_to_open"
        assert data["action"][1] == "sell_to_close"
        assert data["action"][2] == "sell_to_close"

        # Shares should match per-execution deltas
        assert data["shares"][0] == 134.0
        assert data["shares"][1] == 67.0
        assert data["shares"][2] == 67.0

        # Verify execution field is present and unique for each row
        assert_execution_field(queue_data, expected_count=3)
        # Each execution should be unique
        assert len(set(data["execution"])) == 3


class TestResultsWriterWriteStudies:
    """Test write_studies method."""

    @pytest.mark.unit
    def test_write_studies_empty(self, results_writer, mock_queue_broker):
        """Test writing empty studies DataFrame."""
        writer = results_writer

        result = writer.write_studies(
            studies=pd.DataFrame(),
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        mock_queue_broker.enqueue.assert_not_called()

    @pytest.mark.unit
    def test_write_studies_success(
        self, results_writer, mock_queue_broker, sample_studies_data_minimal, execution_config
    ):
        """Test writing studies successfully."""
        writer = results_writer
        result = writer.write_studies(
            studies=sample_studies_data_minimal,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={"short_window": 10},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert result is True
        mock_queue_broker.enqueue.assert_called_once()
        call_args = mock_queue_broker.enqueue.call_args
        assert call_args[1]["queue_name"] == BACKTEST_STUDIES_QUEUE_NAME
        assert call_args[1]["ttl"] == BACKTEST_REDIS_TTL
        assert "hash_id" in call_args[1]["data"]

    @pytest.mark.unit
    def test_write_studies_with_hash(
        self,
        results_writer,
        mock_queue_broker,
        sample_studies_data_minimal,
        standard_backtest_params,
        standard_backtest_hash_id,
    ):
        """Test writing studies with backtest hash computation."""
        writer = results_writer
        strategy_params = {"short_window": 10, "long_window": 20}

        # Compute hash for this specific strategy_params
        hash_id = compute_backtest_hash(
            strategy_params=strategy_params,
            execution_config=standard_backtest_params["execution_config"],
            start_date=standard_backtest_params["start_date"],
            end_date=standard_backtest_params["end_date"],
            step_frequency=standard_backtest_params["step_frequency"],
            database="debug",
            tickers=standard_backtest_params["tickers"],
            capital_per_trade=standard_backtest_params["capital_per_trade"],
            risk_free_rate=standard_backtest_params["risk_free_rate"],
            walk_forward=standard_backtest_params["walk_forward"],
            train_days=standard_backtest_params["train_days"],
            test_days=standard_backtest_params["test_days"],
            train_split=standard_backtest_params["train_split"],
            filter_params=standard_backtest_params["filter_params"],
        )

        result = writer.write_studies(
            studies=sample_studies_data_minimal,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params=strategy_params,
            execution_config=standard_backtest_params["execution_config"],
            start_date=standard_backtest_params["start_date"],
            end_date=standard_backtest_params["end_date"],
            step_frequency=standard_backtest_params["step_frequency"],
            database="debug",
            tickers=standard_backtest_params["tickers"],
            capital_per_trade=standard_backtest_params["capital_per_trade"],
            risk_free_rate=standard_backtest_params["risk_free_rate"],
            hash_id=hash_id,
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["hash_id"] == hash_id
        assert len(queue_data["hash_id"]) == 16  # 16-char hex hash

    @pytest.mark.unit
    def test_write_studies_without_hash_params(
        self, results_writer, mock_queue_broker, sample_studies_data_single
    ):
        """Test writing studies without hash computation parameters."""
        writer = results_writer

        result = writer.write_studies(
            studies=sample_studies_data_single,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["hash_id"] is None

    @pytest.mark.unit
    def test_write_studies_failure(
        self, results_writer, mock_queue_broker, sample_studies_data_single
    ):
        """Test writing studies failure."""
        writer = results_writer
        mock_queue_broker.enqueue.return_value = False

        result = writer.write_studies(
            studies=sample_studies_data_single,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_studies_exception(
        self, results_writer, mock_queue_broker, sample_studies_data_single
    ):
        """Test writing studies exception handling."""
        writer = results_writer
        mock_queue_broker.enqueue.side_effect = Exception("Redis error")

        result = writer.write_studies(
            studies=sample_studies_data_single,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_studies_schema_validation_failure(self, results_writer, mock_queue_broker):
        """Test that schema validation failure prevents enqueue."""
        writer = results_writer

        studies = pd.DataFrame(
            {
                "close": [100.0, 101.0],
                "sma_10": [99.0],
            },
            index=[
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-06", tz="UTC"),
            ],
        )

        # Force an invalid time-series payload with mismatched column lengths.
        with patch(
            "system.algo_trader.backtest.results.writer.dataframe_to_dict"
        ) as mock_df_to_dict:
            mock_df_to_dict.return_value = {
                "datetime": [1704067200000, 1704153600000],  # two timestamps
                "sma_10": [99.0],  # only one value -> length mismatch
            }

            result = writer.write_studies(
                studies=studies,
                strategy_name="TestStrategy",
                ticker="AAPL",
            )

        assert result is False
        mock_queue_broker.enqueue.assert_not_called()

    @pytest.mark.unit
    def test_write_studies_invalid_strategy_params(
        self, results_writer, mock_queue_broker, sample_studies_data_single
    ):
        """Test that invalid strategy_params keys cause validation failure."""
        writer = results_writer

        # strategy_params with an empty key should fail BacktestStudiesPayload validation.
        result = writer.write_studies(
            studies=sample_studies_data_single,
            strategy_name="TestStrategy",
            ticker="AAPL",
            strategy_params={"": 10},
        )

        assert result is False
        mock_queue_broker.enqueue.assert_not_called()

    @pytest.mark.unit
    def test_write_studies_walk_forward_hash(
        self,
        results_writer,
        mock_queue_broker,
        sample_studies_data_single,
        walk_forward_backtest_params,
        walk_forward_backtest_hash_id,
    ):
        """Test hash computation includes walk-forward parameters."""
        writer = results_writer

        result = writer.write_studies(
            studies=sample_studies_data_single,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params=walk_forward_backtest_params["strategy_params"],
            execution_config=walk_forward_backtest_params["execution_config"],
            start_date=walk_forward_backtest_params["start_date"],
            end_date=walk_forward_backtest_params["end_date"],
            step_frequency=walk_forward_backtest_params["step_frequency"],
            database=walk_forward_backtest_params["database"],
            tickers=walk_forward_backtest_params["tickers"],
            capital_per_trade=walk_forward_backtest_params["capital_per_trade"],
            risk_free_rate=walk_forward_backtest_params["risk_free_rate"],
            walk_forward=walk_forward_backtest_params["walk_forward"],
            train_days=walk_forward_backtest_params["train_days"],
            test_days=walk_forward_backtest_params["test_days"],
            train_split=walk_forward_backtest_params["train_split"],
            hash_id=walk_forward_backtest_hash_id,
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["hash_id"] == walk_forward_backtest_hash_id

    @pytest.mark.integration
    def test_write_studies_complete_workflow(
        self, results_writer, mock_queue_broker, sample_studies_data, execution_config
    ):
        """Test complete workflow: DataFrame → dict → Redis."""
        writer = results_writer

        result = writer.write_studies(
            studies=sample_studies_data,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={"short_window": 10, "long_window": 20},
            execution_config=execution_config,
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        assert call_args[1]["queue_name"] == BACKTEST_STUDIES_QUEUE_NAME
        assert call_args[1]["item_id"] == "AAPL_TestStrategy_test-id_studies"
        queue_data = call_args[1]["data"]
        assert queue_data["ticker"] == "AAPL"
        assert queue_data["strategy_name"] == "TestStrategy"
        assert queue_data["backtest_id"] == "test-id"
        assert queue_data["database"] == "debug"
        assert queue_data["strategy_params"] == {"short_window": 10, "long_window": 20}
        assert len(queue_data["data"]["datetime"]) == 3
        assert "sma_10" in queue_data["data"]
        assert len(queue_data["data"]["sma_10"]) == 3
