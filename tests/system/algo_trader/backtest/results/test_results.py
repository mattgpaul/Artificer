"""Unit tests for ResultsWriter.

Tests cover trade/metrics writing, backtest hash computation, and Redis queue integration.
.
"""

import pandas as pd

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.results.hash import compute_backtest_hash
from system.algo_trader.backtest.results.writer import ResultsWriter


class TestResultsWriter:
    """Test ResultsWriter operations."""

    def test_initialization(self, mock_queue_broker):
        """Test ResultsWriter initialization."""
        writer = ResultsWriter()
        assert writer.namespace == "queue"
        assert writer.queue_broker is not None

    def test_initialization_custom_namespace(self, mock_queue_broker):
        """Test ResultsWriter initialization with custom namespace."""
        writer = ResultsWriter(namespace="custom")
        assert writer.namespace == "custom"

    def test_compute_backtest_hash(self, mock_queue_broker):
        """Test backtest hash computation."""
        execution_config = ExecutionConfig(slippage_bps=5.0, commission_per_share=0.005)
        strategy_params = {"short_window": 10, "long_window": 20}
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        hash1 = compute_backtest_hash(
            strategy_params=strategy_params,
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="test_db",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        # Same parameters should produce same hash
        hash2 = compute_backtest_hash(
            strategy_params=strategy_params,
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="test_db",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_compute_backtest_hash_different_params(self, mock_queue_broker):
        """Test backtest hash differs with different parameters."""
        execution_config = ExecutionConfig(slippage_bps=5.0, commission_per_share=0.005)
        strategy_params1 = {"short_window": 10, "long_window": 20}
        strategy_params2 = {"short_window": 15, "long_window": 25}
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        hash1 = compute_backtest_hash(
            strategy_params=strategy_params1,
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="test_db",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        hash2 = compute_backtest_hash(
            strategy_params=strategy_params2,
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="test_db",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert hash1 != hash2

    def test_write_trades_empty_dataframe(self, mock_queue_broker):
        """Test write_trades with empty DataFrame."""
        writer = ResultsWriter()

        empty_trades = pd.DataFrame()
        result = writer.write_trades(
            trades=empty_trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is True

    def test_write_trades_success(self, mock_queue_broker, sample_trades):
        """Test write_trades with valid trades."""
        writer = ResultsWriter()
        mock_queue_broker.enqueue.return_value = True

        execution_config = ExecutionConfig()
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        result = writer.write_trades(
            trades=sample_trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={"short_window": 10},
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="test_db",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert result is True
        mock_queue_broker.enqueue.assert_called_once()

    def test_write_trades_failure(self, mock_queue_broker, sample_trades):
        """Test write_trades when Redis enqueue fails."""
        writer = ResultsWriter()
        mock_queue_broker.enqueue.return_value = False

        result = writer.write_trades(
            trades=sample_trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    def test_write_trades_exception(self, mock_queue_broker, sample_trades):
        """Test write_trades exception handling."""
        writer = ResultsWriter()
        mock_queue_broker.enqueue.side_effect = Exception("Redis error")

        result = writer.write_trades(
            trades=sample_trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    def test_write_metrics_success(self, mock_queue_broker):
        """Test write_metrics with valid metrics."""
        writer = ResultsWriter()
        mock_queue_broker.enqueue.return_value = True

        metrics = {
            "total_trades": 10,
            "total_profit": 1000.0,
            "total_profit_pct": 10.0,
            "max_drawdown": 5.0,
            "sharpe_ratio": 1.5,
            "win_rate": 60.0,
            "avg_efficiency": 80.0,
            "avg_return_pct": 2.0,
            "avg_time_held": 5.0,
        }

        execution_config = ExecutionConfig()
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={"short_window": 10},
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="test_db",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert result is True
        mock_queue_broker.enqueue.assert_called_once()

    def test_write_metrics_failure(self, mock_queue_broker):
        """Test write_metrics when Redis enqueue fails."""
        writer = ResultsWriter()
        mock_queue_broker.enqueue.return_value = False

        metrics = {"total_trades": 10}

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    def test_write_metrics_exception(self, mock_queue_broker):
        """Test write_metrics exception handling."""
        writer = ResultsWriter()
        mock_queue_broker.enqueue.side_effect = Exception("Redis error")

        metrics = {"total_trades": 10}

        result = writer.write_metrics(
            metrics=metrics,
            strategy_name="TestStrategy",
            ticker="AAPL",
        )

        assert result is False

    def test_write_trades_with_backtest_hash(self, mock_queue_broker, sample_trades):
        """Test write_trades includes backtest_hash when all params provided."""
        writer = ResultsWriter()
        mock_queue_broker.enqueue.return_value = True

        execution_config = ExecutionConfig()
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        writer.write_trades(
            trades=sample_trades,
            strategy_name="TestStrategy",
            ticker="AAPL",
            backtest_id="test-id",
            strategy_params={"short_window": 10},
            execution_config=execution_config,
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="test_db",
            tickers=["AAPL"],
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        # Verify enqueue was called with backtest_hash
        call_args = mock_queue_broker.enqueue.call_args
        queue_data = call_args[1]["data"]
        assert "backtest_hash" in queue_data
        assert queue_data["backtest_hash"] is not None
