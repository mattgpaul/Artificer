"""Unit and integration tests for backtest worker functions.

Tests cover strategy creation, result logging, result writing, and complete worker
workflow. All external dependencies are mocked via conftest.py. Integration tests
use 'debug' database.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.engine import BacktestResults
from system.algo_trader.backtest.processor.worker import (
    backtest_ticker_worker,
    create_strategy_instance,
    log_backtest_results,
    write_backtest_results,
)


class TestCreateStrategyInstance:
    """Test create_strategy_instance function."""

    @pytest.mark.unit
    def test_create_strategy_instance_sma_crossover(self):
        """Test creating SMA crossover strategy instance."""
        with patch(
            "system.algo_trader.backtest.processor.worker.get_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_strategy = MagicMock()
            mock_registry.create_strategy_from_params.return_value = mock_strategy
            mock_get_registry.return_value = mock_registry

            result = create_strategy_instance("SMACrossover", {"short": 10, "long": 20})

            assert result == mock_strategy
            mock_registry.create_strategy_from_params.assert_called_once_with(
                "SMACrossover", {"short": 10, "long": 20}
            )

    @pytest.mark.unit
    def test_create_strategy_instance_unknown_type(self):
        """Test creating unknown strategy type raises ValueError."""
        with patch(
            "system.algo_trader.backtest.processor.worker.get_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.create_strategy_from_params.side_effect = ValueError(
                "Unknown strategy type: 'UnknownStrategy'"
            )
            mock_get_registry.return_value = mock_registry

            with pytest.raises(ValueError, match="Unknown strategy"):
                create_strategy_instance("UnknownStrategy", {})

    @pytest.mark.unit
    def test_create_strategy_instance_missing_params(self):
        """Test creating strategy with missing parameters."""
        with patch(
            "system.algo_trader.backtest.processor.worker.get_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.create_strategy_from_params.side_effect = ValueError(
                "Failed to create strategy UnknownStrategy: Missing parameter"
            )
            mock_get_registry.return_value = mock_registry

            with pytest.raises(ValueError):
                create_strategy_instance("SMACrossover", {})


class TestLogBacktestResults:
    """Test log_backtest_results function."""

    @pytest.mark.unit
    def test_log_backtest_results_with_metrics(self):
        """Test logging results with metrics."""
        with patch("system.algo_trader.backtest.processor.worker.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            results = BacktestResults()
            results.strategy_name = "TestStrategy"
            results.metrics = {
                "total_trades": 10,
                "total_profit": 5000.0,
                "total_profit_pct": 50.0,
                "max_drawdown": 5.0,
                "sharpe_ratio": 1.5,
                "win_rate": 60.0,
                "avg_efficiency": 75.0,
            }

            log_backtest_results("AAPL", results)

            mock_logger.debug.assert_called_once()
            call_args_str = str(mock_logger.debug.call_args)
            assert "AAPL" in call_args_str
            assert "TestStrategy" in call_args_str
            assert "10" in call_args_str
            assert "5000" in call_args_str

    @pytest.mark.unit
    def test_log_backtest_results_no_metrics(self):
        """Test logging results without metrics."""
        with patch("system.algo_trader.backtest.processor.worker.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            results = BacktestResults()
            results.metrics = {}

            log_backtest_results("AAPL", results)

            mock_logger.debug.assert_not_called()

    @pytest.mark.unit
    def test_log_backtest_results_partial_metrics(self):
        """Test logging results with partial metrics."""
        with patch("system.algo_trader.backtest.processor.worker.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            results = BacktestResults()
            results.strategy_name = "TestStrategy"
            results.metrics = {"total_trades": 5}

            log_backtest_results("AAPL", results)

            mock_logger.debug.assert_called_once()


class TestWriteBacktestResults:
    """Test write_backtest_results function."""

    @pytest.mark.unit
    def test_write_backtest_results_success(self):
        """Test writing results successfully."""
        with patch(
            "system.algo_trader.backtest.processor.worker.ResultsWriter"
        ) as mock_writer_class:
            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = True
            mock_writer.write_studies.return_value = True
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
            results.studies = pd.DataFrame()
            results.strategy_name = "TestStrategy"

            execution_config = ExecutionConfig()
            result = write_backtest_results(
                results=results,
                ticker="AAPL",
                backtest_id="test-id",
                strategy_params={},
                execution_config=execution_config,
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="debug",
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                walk_forward=False,
                train_days=None,
                test_days=None,
                train_split=None,
            )

            assert result is True
            mock_writer.write_trades.assert_called_once()
            mock_writer.write_studies.assert_called_once()

    @pytest.mark.unit
    def test_write_backtest_results_with_studies(self):
        """Test writing results with studies data."""
        with patch(
            "system.algo_trader.backtest.processor.worker.ResultsWriter"
        ) as mock_writer_class:
            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = True
            mock_writer.write_studies.return_value = True
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
            results.studies = pd.DataFrame(
                {
                    "close": [100.0, 101.0],
                    "sma_10": [99.0, 100.0],
                },
                index=[
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
            )
            results.strategy_name = "TestStrategy"

            execution_config = ExecutionConfig()
            result = write_backtest_results(
                results=results,
                ticker="AAPL",
                backtest_id="test-id",
                strategy_params={},
                execution_config=execution_config,
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="debug",
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                walk_forward=False,
                train_days=None,
                test_days=None,
                train_split=None,
            )

            assert result is True
            mock_writer.write_trades.assert_called_once()
            mock_writer.write_studies.assert_called_once()
            # Verify studies were passed correctly
            studies_call = mock_writer.write_studies.call_args
            assert studies_call[1]["studies"].equals(results.studies)
            assert studies_call[1]["ticker"] == "AAPL"
            assert studies_call[1]["strategy_name"] == "TestStrategy"

    @pytest.mark.unit
    def test_write_backtest_results_empty_trades(self):
        """Test writing results with empty trades."""
        with patch(
            "system.algo_trader.backtest.processor.worker.ResultsWriter"
        ) as mock_writer_class:
            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = True
            mock_writer.write_studies.return_value = True
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame()
            results.studies = pd.DataFrame()
            results.strategy_name = "TestStrategy"

            execution_config = ExecutionConfig()
            result = write_backtest_results(
                results=results,
                ticker="AAPL",
                backtest_id="test-id",
                strategy_params={},
                execution_config=execution_config,
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="debug",
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                walk_forward=False,
                train_days=None,
                test_days=None,
                train_split=None,
            )

            assert result is True
            # Should still call write_trades and write_studies even with empty DataFrames
            mock_writer.write_trades.assert_called_once()
            mock_writer.write_studies.assert_called_once()

    @pytest.mark.unit
    def test_write_backtest_results_failure(self):
        """Test writing results failure."""
        with patch(
            "system.algo_trader.backtest.processor.worker.ResultsWriter"
        ) as mock_writer_class:
            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = False
            mock_writer.write_studies.return_value = True
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
            results.studies = pd.DataFrame()
            results.strategy_name = "TestStrategy"

            execution_config = ExecutionConfig()
            result = write_backtest_results(
                results=results,
                ticker="AAPL",
                backtest_id="test-id",
                strategy_params={},
                execution_config=execution_config,
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="debug",
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                walk_forward=False,
                train_days=None,
                test_days=None,
                train_split=None,
            )

            assert result is False
            # Should still call write_studies even if trades fail
            mock_writer.write_studies.assert_called_once()

    @pytest.mark.unit
    def test_write_backtest_results_walk_forward(self):
        """Test writing results with walk-forward parameters."""
        with patch(
            "system.algo_trader.backtest.processor.worker.ResultsWriter"
        ) as mock_writer_class:
            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = True
            mock_writer.write_studies.return_value = True
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
            results.studies = pd.DataFrame()
            results.strategy_name = "TestStrategy"

            execution_config = ExecutionConfig()
            result = write_backtest_results(
                results=results,
                ticker="AAPL",
                backtest_id="test-id",
                strategy_params={},
                execution_config=execution_config,
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="debug",
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                walk_forward=True,
                train_days=90,
                test_days=30,
                train_split=None,
            )

            assert result is True
            call_args = mock_writer.write_trades.call_args
            assert call_args[1]["walk_forward"] is True
            assert call_args[1]["train_days"] == 90
            assert call_args[1]["test_days"] == 30
            # Verify studies also get walk-forward parameters
            studies_call = mock_writer.write_studies.call_args
            assert studies_call[1]["walk_forward"] is True
            assert studies_call[1]["train_days"] == 90
            assert studies_call[1]["test_days"] == 30


class TestBacktestTickerWorker:
    """Test backtest_ticker_worker function."""

    @pytest.mark.unit
    def test_backtest_ticker_worker_success(
        self,
        mock_dependencies_worker,
        mock_strategy,
        mock_backtest_engine,
        mock_backtest_results_with_trades,
        default_worker_args,
    ):
        """Test worker function with successful execution."""
        deps = mock_dependencies_worker
        deps["create_strategy"].return_value = mock_strategy
        deps["engine_class"].return_value = mock_backtest_engine
        mock_backtest_engine.run_ticker.return_value = mock_backtest_results_with_trades
        deps["write_results"].return_value = True

        result = backtest_ticker_worker(default_worker_args)

        assert result["success"] is True
        assert result["trades"] == 1
        mock_backtest_engine.run_ticker.assert_called_once_with("AAPL")
        deps["write_results"].assert_called_once()
        mock_backtest_engine.influx_client.close.assert_called_once()
        mock_strategy.close.assert_called_once()

    @pytest.mark.unit
    def test_backtest_ticker_worker_no_trades(
        self,
        mock_dependencies_worker,
        mock_strategy,
        mock_backtest_engine,
        mock_backtest_results_empty,
        default_worker_args,
    ):
        """Test worker function when no trades generated."""
        deps = mock_dependencies_worker
        deps["create_strategy"].return_value = mock_strategy
        deps["engine_class"].return_value = mock_backtest_engine
        mock_backtest_engine.run_ticker.return_value = mock_backtest_results_empty

        result = backtest_ticker_worker(default_worker_args)

        assert result["success"] is True
        assert result["trades"] == 0
        deps["write_results"].assert_not_called()

    @pytest.mark.unit
    def test_backtest_ticker_worker_write_failure(
        self,
        mock_dependencies_worker,
        mock_strategy,
        mock_backtest_engine,
        mock_backtest_results_with_trades,
        default_worker_args,
    ):
        """Test worker function when write fails."""
        deps = mock_dependencies_worker
        deps["create_strategy"].return_value = mock_strategy
        deps["engine_class"].return_value = mock_backtest_engine
        mock_backtest_engine.run_ticker.return_value = mock_backtest_results_with_trades
        deps["write_results"].return_value = False

        result = backtest_ticker_worker(default_worker_args)

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Redis enqueue failed"

    @pytest.mark.unit
    def test_backtest_ticker_worker_exception(self, mock_dependencies_worker, default_worker_args):
        """Test worker function exception handling."""
        deps = mock_dependencies_worker
        deps["create_strategy"].side_effect = ValueError("Strategy creation error")

        result = backtest_ticker_worker(default_worker_args)

        assert result["success"] is False
        assert "error" in result
        assert "Strategy creation error" in result["error"]

    @pytest.mark.unit
    def test_backtest_ticker_worker_cleanup_on_exception(
        self,
        mock_dependencies_worker,
        mock_strategy,
        mock_backtest_engine,
        default_worker_args,
    ):
        """Test worker function cleanup on exception."""
        deps = mock_dependencies_worker
        deps["create_strategy"].return_value = mock_strategy
        deps["engine_class"].return_value = mock_backtest_engine
        mock_backtest_engine.run_ticker.side_effect = Exception("Engine error")

        result = backtest_ticker_worker(default_worker_args)

        assert result["success"] is False
        # Should still cleanup
        mock_backtest_engine.influx_client.close.assert_called_once()
        mock_strategy.close.assert_called_once()

    @pytest.mark.unit
    def test_backtest_ticker_worker_cleanup_close_error(
        self,
        mock_dependencies_worker,
        mock_strategy,
        mock_backtest_engine,
        mock_backtest_results_with_trades,
        default_worker_args,
    ):
        """Test worker function handles cleanup errors gracefully."""
        deps = mock_dependencies_worker
        deps["create_strategy"].return_value = mock_strategy
        deps["engine_class"].return_value = mock_backtest_engine
        mock_backtest_engine.run_ticker.return_value = mock_backtest_results_with_trades
        mock_backtest_engine.influx_client.close.side_effect = Exception("Close error")
        deps["write_results"].return_value = True

        # Should not raise exception
        result = backtest_ticker_worker(default_worker_args)

        assert result["success"] is True

    @pytest.mark.integration
    def test_backtest_ticker_worker_complete_workflow(
        self,
        mock_dependencies_worker,
        mock_strategy,
        mock_backtest_engine,
        default_worker_args,
    ):
        """Test complete worker workflow: create → run → write."""
        deps = mock_dependencies_worker
        deps["create_strategy"].return_value = mock_strategy
        deps["engine_class"].return_value = mock_backtest_engine

        mock_results = BacktestResults()
        mock_results.trades = pd.DataFrame(
            {
                "ticker": ["AAPL"] * 5,
                "gross_pnl": [100.0, 200.0, -50.0, 150.0, 75.0],
            }
        )
        mock_results.metrics = {"total_trades": 5, "total_profit": 475.0}
        mock_results.strategy_name = "SMACrossover"
        mock_backtest_engine.run_ticker.return_value = mock_results
        deps["write_results"].return_value = True

        result = backtest_ticker_worker(default_worker_args)

        assert result["success"] is True
        assert result["trades"] == 5
        deps["create_strategy"].assert_called_once()
        mock_backtest_engine.run_ticker.assert_called_once()
        deps["log_results"].assert_called_once()
        deps["write_results"].assert_called_once()
        mock_backtest_engine.influx_client.close.assert_called_once()
        mock_strategy.close.assert_called_once()

    @pytest.mark.integration
    def test_backtest_ticker_worker_account_tracking(
        self,
        mock_dependencies_worker,
        mock_strategy,
        mock_backtest_engine,
        mock_backtest_results_empty,
        worker_args_with_account_tracking,
    ):
        """Test worker with account value tracking."""
        deps = mock_dependencies_worker
        deps["create_strategy"].return_value = mock_strategy
        deps["engine_class"].return_value = mock_backtest_engine
        mock_backtest_engine.run_ticker.return_value = mock_backtest_results_empty

        result = backtest_ticker_worker(worker_args_with_account_tracking)

        assert result["success"] is True
        # Verify account tracking parameters passed to engine
        call_args = deps["engine_class"].call_args
        assert call_args[1]["initial_account_value"] == 50000.0
        assert call_args[1]["trade_percentage"] == 0.10

    @pytest.mark.integration
    def test_backtest_ticker_worker_walk_forward(
        self,
        mock_dependencies_worker,
        mock_strategy,
        mock_backtest_engine,
        mock_backtest_results_with_trades,
        worker_args_with_walk_forward,
    ):
        """Test worker with walk-forward parameters."""
        deps = mock_dependencies_worker
        deps["create_strategy"].return_value = mock_strategy
        deps["engine_class"].return_value = mock_backtest_engine
        mock_backtest_engine.run_ticker.return_value = mock_backtest_results_with_trades
        deps["write_results"].return_value = True

        result = backtest_ticker_worker(worker_args_with_walk_forward)

        assert result["success"] is True
        # Verify walk-forward parameters passed to write_backtest_results
        call_args = deps["write_results"].call_args
        assert call_args[1]["walk_forward"] is True
        assert call_args[1]["train_days"] == 90
        assert call_args[1]["test_days"] == 30
