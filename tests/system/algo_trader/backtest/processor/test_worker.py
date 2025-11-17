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
            "system.algo_trader.backtest.processor.worker.SMACrossover"
        ) as mock_strategy_class:
            mock_strategy = MagicMock()
            mock_strategy_class.return_value = mock_strategy

            result = create_strategy_instance(
                "SMACrossover", {"short_window": 10, "long_window": 20}
            )

            assert result == mock_strategy
            mock_strategy_class.assert_called_once_with(short_window=10, long_window=20)

    @pytest.mark.unit
    def test_create_strategy_instance_unknown_type(self):
        """Test creating unknown strategy type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy type"):
            create_strategy_instance("UnknownStrategy", {})

    @pytest.mark.unit
    def test_create_strategy_instance_missing_params(self):
        """Test creating strategy with missing parameters."""
        with patch(
            "system.algo_trader.backtest.processor.worker.SMACrossover"
        ) as mock_strategy_class:
            mock_strategy_class.side_effect = KeyError("Missing parameter")

            with pytest.raises(KeyError):
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

            mock_logger.info.assert_called_once()
            call_args_str = str(mock_logger.info.call_args)
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

            mock_logger.info.assert_not_called()

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

            mock_logger.info.assert_called_once()


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
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
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

    @pytest.mark.unit
    def test_write_backtest_results_empty_trades(self):
        """Test writing results with empty trades."""
        with patch(
            "system.algo_trader.backtest.processor.worker.ResultsWriter"
        ) as mock_writer_class:
            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = True
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame()
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
            # Should still call write_trades even with empty DataFrame
            mock_writer.write_trades.assert_called_once()

    @pytest.mark.unit
    def test_write_backtest_results_failure(self):
        """Test writing results failure."""
        with patch(
            "system.algo_trader.backtest.processor.worker.ResultsWriter"
        ) as mock_writer_class:
            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = False
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
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

    @pytest.mark.unit
    def test_write_backtest_results_walk_forward(self):
        """Test writing results with walk-forward parameters."""
        with patch(
            "system.algo_trader.backtest.processor.worker.ResultsWriter"
        ) as mock_writer_class:
            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = True
            mock_writer_class.return_value = mock_writer

            results = BacktestResults()
            results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
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


class TestBacktestTickerWorker:
    """Test backtest_ticker_worker function."""

    @pytest.mark.unit
    def test_backtest_ticker_worker_success(self):
        """Test worker function with successful execution."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.create_strategy_instance"
            ) as mock_create_strategy,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch(
                "system.algo_trader.backtest.processor.worker.write_backtest_results"
            ) as mock_write_results,
            patch(
                "system.algo_trader.backtest.processor.worker.log_backtest_results"
            ) as _mock_log_results,
        ):
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create_strategy.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = BacktestResults()
            mock_results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
            mock_results.metrics = {"total_trades": 1}
            mock_results.strategy_name = "SMACrossover"
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close = MagicMock()
            mock_engine_class.return_value = mock_engine

            mock_write_results.return_value = True

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is True
            assert result["trades"] == 1
            mock_engine.run_ticker.assert_called_once_with("AAPL")
            mock_write_results.assert_called_once()
            mock_engine.influx_client.close.assert_called_once()
            mock_strategy.close.assert_called_once()

    @pytest.mark.unit
    def test_backtest_ticker_worker_no_trades(self):
        """Test worker function when no trades generated."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.create_strategy_instance"
            ) as mock_create_strategy,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch(
                "system.algo_trader.backtest.processor.worker.write_backtest_results"
            ) as mock_write_results,
        ):
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create_strategy.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = BacktestResults()
            mock_results.trades = pd.DataFrame()  # Empty trades
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close = MagicMock()
            mock_engine_class.return_value = mock_engine

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is True
            assert result["trades"] == 0
            mock_write_results.assert_not_called()

    @pytest.mark.unit
    def test_backtest_ticker_worker_write_failure(self):
        """Test worker function when write fails."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.create_strategy_instance"
            ) as mock_create_strategy,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch(
                "system.algo_trader.backtest.processor.worker.write_backtest_results"
            ) as mock_write_results,
            patch(
                "system.algo_trader.backtest.processor.worker.log_backtest_results"
            ) as _mock_log_results,
        ):
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create_strategy.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = BacktestResults()
            mock_results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
            mock_results.metrics = {"total_trades": 1}
            mock_results.strategy_name = "SMACrossover"
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close = MagicMock()
            mock_engine_class.return_value = mock_engine

            mock_write_results.return_value = False

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is False
            assert "error" in result
            assert result["error"] == "Redis enqueue failed"

    @pytest.mark.unit
    def test_backtest_ticker_worker_exception(self):
        """Test worker function exception handling."""
        with patch(
            "system.algo_trader.backtest.processor.worker.create_strategy_instance"
        ) as mock_create_strategy:
            mock_create_strategy.side_effect = ValueError("Strategy creation error")

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is False
            assert "error" in result
            assert "Strategy creation error" in result["error"]

    @pytest.mark.unit
    def test_backtest_ticker_worker_cleanup_on_exception(self):
        """Test worker function cleanup on exception."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.create_strategy_instance"
            ) as mock_create_strategy,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
        ):
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create_strategy.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_engine.run_ticker.side_effect = Exception("Engine error")
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close = MagicMock()
            mock_engine_class.return_value = mock_engine

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is False
            # Should still cleanup
            mock_engine.influx_client.close.assert_called_once()
            mock_strategy.close.assert_called_once()

    @pytest.mark.unit
    def test_backtest_ticker_worker_cleanup_close_error(self):
        """Test worker function handles cleanup errors gracefully."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.create_strategy_instance"
            ) as mock_create_strategy,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch(
                "system.algo_trader.backtest.processor.worker.write_backtest_results"
            ) as mock_write_results,
        ):
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create_strategy.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = BacktestResults()
            mock_results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
            mock_results.strategy_name = "SMACrossover"
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close.side_effect = Exception("Close error")
            mock_engine_class.return_value = mock_engine

            mock_write_results.return_value = True

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
                None,
                None,
            )

            # Should not raise exception
            result = backtest_ticker_worker(args)

            assert result["success"] is True

    @pytest.mark.integration
    def test_backtest_ticker_worker_complete_workflow(self):
        """Test complete worker workflow: create → run → write."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.create_strategy_instance"
            ) as mock_create_strategy,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch(
                "system.algo_trader.backtest.processor.worker.write_backtest_results"
            ) as mock_write_results,
            patch(
                "system.algo_trader.backtest.processor.worker.log_backtest_results"
            ) as mock_log_results,
        ):
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create_strategy.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = BacktestResults()
            mock_results.trades = pd.DataFrame(
                {
                    "ticker": ["AAPL"] * 5,
                    "gross_pnl": [100.0, 200.0, -50.0, 150.0, 75.0],
                }
            )
            mock_results.metrics = {"total_trades": 5, "total_profit": 475.0}
            mock_results.strategy_name = "SMACrossover"
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close = MagicMock()
            mock_engine_class.return_value = mock_engine

            mock_write_results.return_value = True

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "debug",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is True
            assert result["trades"] == 5
            mock_create_strategy.assert_called_once()
            mock_engine.run_ticker.assert_called_once()
            mock_log_results.assert_called_once()
            mock_write_results.assert_called_once()
            mock_engine.influx_client.close.assert_called_once()
            mock_strategy.close.assert_called_once()

    @pytest.mark.integration
    def test_backtest_ticker_worker_account_tracking(self):
        """Test worker with account value tracking."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.create_strategy_instance"
            ) as mock_create_strategy,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch(
                "system.algo_trader.backtest.processor.worker.write_backtest_results"
            ) as mock_write_results,
        ):
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create_strategy.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = BacktestResults()
            mock_results.trades = pd.DataFrame()
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close = MagicMock()
            mock_engine_class.return_value = mock_engine

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "debug",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
                50000.0,
                0.10,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is True
            # Verify account tracking parameters passed to engine
            call_args = mock_engine_class.call_args
            assert call_args[1]["initial_account_value"] == 50000.0
            assert call_args[1]["trade_percentage"] == 0.10

    @pytest.mark.integration
    def test_backtest_ticker_worker_walk_forward(self):
        """Test worker with walk-forward parameters."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.create_strategy_instance"
            ) as mock_create_strategy,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch(
                "system.algo_trader.backtest.processor.worker.write_backtest_results"
            ) as mock_write_results,
        ):
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create_strategy.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = BacktestResults()
            mock_results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
            mock_results.strategy_name = "SMACrossover"
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close = MagicMock()
            mock_engine_class.return_value = mock_engine

            mock_write_results.return_value = True

            args = (
                "AAPL",
                "SMACrossover",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-12-31", tz="UTC"),
                "daily",
                "debug",
                "debug",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                True,
                90,
                30,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is True
            # Verify walk-forward parameters passed to write_backtest_results
            call_args = mock_write_results.call_args
            assert call_args[1]["walk_forward"] is True
            assert call_args[1]["train_days"] == 90
            assert call_args[1]["test_days"] == 30
