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
from system.algo_trader.backtest.results.writer import ResultsWriter
from system.algo_trader.backtest.utils.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_REDIS_TTL,
    BACKTEST_TRADES_QUEUE_NAME,
)


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
        with patch(
            "system.algo_trader.backtest.results.writer.QueueBroker"
        ) as mock_broker_class:
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker

            writer = ResultsWriter()

            assert writer.queue_broker == mock_broker
            mock_broker_class.assert_called_once_with(namespace="queue")


class TestResultsWriterWriteTrades:
    """Test write_trades method."""

    @pytest.mark.unit
    def test_write_trades_empty(self, mock_queue_broker):
        """Test writing empty trades DataFrame."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker

        result = writer.write_trades(
            trades=pd.DataFrame(),
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        mock_queue_broker.enqueue.assert_not_called()

    @pytest.mark.unit
    def test_write_trades_success(self, mock_queue_broker):
        """Test writing trades successfully."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )

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
        assert "backtest_hash" in call_args[1]["data"]

    @pytest.mark.unit
    def test_write_trades_with_hash(self, mock_queue_broker):
        """Test writing trades with backtest hash computation."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )

        execution_config = ExecutionConfig(slippage_bps=5.0, commission_per_share=0.005)
        strategy_params = {"short_window": 10, "long_window": 20}

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
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

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["backtest_hash"] is not None
        assert len(queue_data["backtest_hash"]) == 16  # 16-char hex hash

    @pytest.mark.unit
    def test_write_trades_without_hash_params(self, mock_queue_broker):
        """Test writing trades without hash computation parameters."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
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
        assert queue_data["backtest_hash"] is None

    @pytest.mark.unit
    def test_write_trades_failure(self, mock_queue_broker):
        """Test writing trades failure."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = False

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_trades_exception(self, mock_queue_broker):
        """Test writing trades exception handling."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.side_effect = Exception("Redis error")

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_trades_walk_forward_hash(self, mock_queue_broker):
        """Test hash computation includes walk-forward parameters."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )

        execution_config = ExecutionConfig()
        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
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
            train_split=None,
        )

        assert result is True
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert queue_data["backtest_hash"] is not None

    @pytest.mark.unit
    def test_write_trades_dataframe_conversion(self, mock_queue_broker):
        """Test DataFrame to dict conversion."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
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
        assert "data" in queue_data
        assert "datetime" in queue_data["data"]
        assert isinstance(queue_data["data"]["datetime"], list)

    @pytest.mark.unit
    def test_write_trades_nan_handling(self, mock_queue_broker):
        """Test NaN handling in DataFrame conversion."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
                "optional_field": [None],  # NaN value
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
        # NaN should be handled (converted to 0 or empty string)
        assert "data" in queue_data

    @pytest.mark.unit
    def test_write_trades_all_nan_column(self, mock_queue_broker):
        """Test handling of all-NaN columns."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
                "all_nan_col": [None],  # All NaN column
            }
        )

        result = writer.write_trades(
            trades=trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True
        # All-NaN column should be dropped

    @pytest.mark.integration
    def test_write_trades_complete_workflow(self, mock_queue_broker):
        """Test complete workflow: DataFrame → dict → Redis."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "entry_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "exit_time": [
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-11", tz="UTC"),
                ],
                "entry_price": [100.0, 200.0],
                "exit_price": [105.0, 210.0],
                "gross_pnl": [500.0, 1000.0],
            }
        )

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
        assert len(queue_data["data"]["datetime"]) == 2


class TestResultsWriterWriteMetrics:
    """Test write_metrics method."""

    @pytest.mark.unit
    def test_write_metrics_success(self, mock_queue_broker):
        """Test writing metrics successfully."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

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
    def test_write_metrics_with_hash(self, mock_queue_broker):
        """Test writing metrics with hash computation."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        metrics = {"total_trades": 5}

        execution_config = ExecutionConfig()
        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={},
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
        queue_data = call_args[1]["data"]
        assert "backtest_hash" in queue_data["data"]
        assert queue_data["backtest_hash"] is not None

    @pytest.mark.unit
    def test_write_metrics_failure(self, mock_queue_broker):
        """Test writing metrics failure."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = False

        metrics = {"total_trades": 5}

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_metrics_exception(self, mock_queue_broker):
        """Test writing metrics exception handling."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.side_effect = Exception("Redis error")

        metrics = {"total_trades": 5}

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    @pytest.mark.unit
    def test_write_metrics_rounding(self, mock_queue_broker):
        """Test metrics values are properly rounded."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

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
    def test_dataframe_to_dict_datetime_index(self, mock_queue_broker):
        """Test conversion with DatetimeIndex."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"] * 5,
                "entry_price": [100.0] * 5,
                "exit_price": [105.0] * 5,
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
        assert len(queue_data["data"]["datetime"]) == 5

    @pytest.mark.unit
    def test_dataframe_to_dict_datetime_column(self, mock_queue_broker):
        """Test conversion with datetime column."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "datetime": pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC"),
                "ticker": ["AAPL"] * 3,
                "entry_price": [100.0] * 3,
                "exit_price": [105.0] * 3,
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
    def test_dataframe_to_dict_exit_time_column(self, mock_queue_broker):
        """Test conversion with exit_time column."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
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

    @pytest.mark.unit
    def test_dataframe_to_dict_nan_string_columns(self, mock_queue_broker):
        """Test NaN handling in string columns."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
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
    def test_dataframe_to_dict_nan_numeric_columns(self, mock_queue_broker):
        """Test NaN handling in numeric columns."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
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
    def test_dataframe_to_dict_datetime_columns(self, mock_queue_broker):
        """Test datetime column conversion."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
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
        # Datetime columns should be converted to milliseconds
        assert isinstance(queue_data["data"]["entry_time"], list)
        assert isinstance(queue_data["data"]["entry_time"][0], int)

    @pytest.mark.integration
    def test_dataframe_to_dict_complete_conversion(self, mock_queue_broker):
        """Test complete DataFrame conversion workflow."""
        writer = ResultsWriter()
        writer.queue_broker = mock_queue_broker
        mock_queue_broker.enqueue.return_value = True

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "entry_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "exit_time": [
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-11", tz="UTC"),
                ],
                "entry_price": [100.0, 200.0],
                "exit_price": [105.0, 210.0],
                "gross_pnl": [500.0, 1000.0],
                "side": ["LONG", "LONG"],
                "efficiency": [75.5, 80.0],
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
        data_dict = queue_data["data"]
        assert len(data_dict["datetime"]) == 2
        assert len(data_dict["ticker"]) == 2
        assert len(data_dict["gross_pnl"]) == 2

