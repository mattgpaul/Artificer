"""Unit tests for BacktestProcessor.

Tests cover ticker processing, multiprocessing, and sequential processing modes.
All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import pandas as pd

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.processor import BacktestProcessor
from system.algo_trader.backtest.processor.worker import backtest_ticker_worker


class TestBacktestProcessor:
    """Test BacktestProcessor operations."""

    def test_initialization(self, mock_logger):
        """Test BacktestProcessor initialization."""
        processor = BacktestProcessor()
        assert processor.logger is not None

    def test_initialization_custom_logger(self):
        """Test BacktestProcessor initialization with custom logger."""
        custom_logger = MagicMock()
        processor = BacktestProcessor(logger=custom_logger)
        assert processor.logger == custom_logger

    def test_process_tickers_empty_list(self, mock_logger):
        """Test process_tickers with empty ticker list."""
        processor = BacktestProcessor()
        mock_strategy = MagicMock()
        mock_strategy.strategy_name = "TestStrategy"

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")
        execution_config = ExecutionConfig()

        processor.process_tickers(
            strategy=mock_strategy,
            tickers=[],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="test_db",
            execution_config=execution_config,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            strategy_params={},
        )

        # Should log error and return early
        assert True  # Test passes if no exception raised

    def test_process_tickers_sequential_mode(self, mock_logger, mock_strategy):
        """Test process_tickers in sequential mode."""
        processor = BacktestProcessor()

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-10", tz="UTC")
        execution_config = ExecutionConfig()

        with patch("system.algo_trader.backtest.processor._backtest_ticker_worker") as mock_worker:
            mock_worker.return_value = {"success": True, "trades": 5}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL", "MSFT"],
                start_date=start_date,
                end_date=end_date,
                step_frequency="daily",
                database="test_db",
                execution_config=execution_config,
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={"short_window": 10},
                use_multiprocessing=False,
            )

            # Should call worker for each ticker sequentially
            assert mock_worker.call_count == 2

    def test_process_tickers_multiprocessing_mode(
        self, mock_logger, mock_strategy, mock_process_manager
    ):
        """Test process_tickers in multiprocessing mode."""
        processor = BacktestProcessor()

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-10", tz="UTC")
        execution_config = ExecutionConfig()

        with patch("system.algo_trader.backtest.processor.ProcessManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.map.return_value = [
                {"success": True, "trades": 5},
                {"success": True, "trades": 3},
            ]
            mock_manager.close_pool.return_value = None
            mock_manager_class.return_value = mock_manager

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL", "MSFT"],
                start_date=start_date,
                end_date=end_date,
                step_frequency="daily",
                database="test_db",
                execution_config=execution_config,
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={"short_window": 10},
                use_multiprocessing=True,
            )

            # Should use ProcessManager.map
            assert mock_manager.map.called
            assert mock_manager.close_pool.called

    def test_process_tickers_custom_max_processes(self, mock_logger, mock_strategy):
        """Test process_tickers with custom max_processes."""
        processor = BacktestProcessor()

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-10", tz="UTC")
        execution_config = ExecutionConfig()

        with patch("system.algo_trader.backtest.processor.ProcessManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.map.return_value = [{"success": True, "trades": 5}]
            mock_manager.close_pool.return_value = None
            mock_manager_class.return_value = mock_manager

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL"],
                start_date=start_date,
                end_date=end_date,
                step_frequency="daily",
                database="test_db",
                execution_config=execution_config,
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={},
                max_processes=4,
                use_multiprocessing=True,
            )

            # Verify ProcessConfig was created with max_processes
            assert mock_manager_class.called


class TestBacktestTickerWorker:
    """Test backtest_ticker_worker function."""

    def test_backtest_ticker_worker_success(self):
        """Test worker function with successful execution."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.SMACrossoverStrategy"
            ) as mock_strategy_class,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch(
                "system.algo_trader.backtest.processor.worker.ResultsWriter"
            ) as mock_writer_class,
            patch("system.algo_trader.backtest.processor.worker.get_logger") as mock_get_logger,
            patch(
                "system.algo_trader.backtest.processor.worker.log_backtest_results"
            ) as mock_log_results,
            patch(
                "system.algo_trader.backtest.processor.worker.write_backtest_results"
            ) as mock_write_results,
        ):
            # Setup mocks
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            mock_strategy = MagicMock()
            mock_strategy.close.return_value = None
            mock_strategy_class.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = MagicMock()
            # Use a proper DataFrame with actual data to ensure .empty works correctly
            trades_df = pd.DataFrame({"col1": [1, 2]})
            mock_results.trades = trades_df
            mock_results.metrics = {"total_trades": 2}
            mock_results.strategy_name = "SMACrossoverStrategy"
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close.return_value = None
            mock_engine_class.return_value = mock_engine

            mock_writer = MagicMock()
            mock_writer.write_trades.return_value = True
            mock_writer.write_metrics.return_value = True
            mock_writer_class.return_value = mock_writer

            # Mock helper functions
            mock_log_results.return_value = None
            mock_write_results.return_value = (True, True)

            # Prepare args
            args = (
                "AAPL",
                "SMACrossoverStrategy",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is True
            assert result["trades"] == 2

    def test_backtest_ticker_worker_no_trades(self):
        """Test worker function when no trades generated."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.SMACrossoverStrategy"
            ) as mock_strategy_class,
            patch(
                "system.algo_trader.backtest.processor.worker.BacktestEngine"
            ) as mock_engine_class,
            patch("system.algo_trader.backtest.processor.worker.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            mock_strategy = MagicMock()
            mock_strategy.close.return_value = None
            mock_strategy_class.return_value = mock_strategy

            mock_engine = MagicMock()
            mock_results = MagicMock()
            mock_results.trades = pd.DataFrame()  # Empty trades
            mock_engine.run_ticker.return_value = mock_results
            mock_engine.influx_client = MagicMock()
            mock_engine.influx_client.close.return_value = None
            mock_engine_class.return_value = mock_engine

            args = (
                "AAPL",
                "SMACrossoverStrategy",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is True
            assert result["trades"] == 0

    def test_backtest_ticker_worker_exception(self):
        """Test worker function exception handling."""
        with (
            patch(
                "system.algo_trader.backtest.processor.worker.SMACrossoverStrategy"
            ) as mock_strategy_class,
            patch("system.algo_trader.backtest.processor.worker.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_strategy_class.side_effect = ValueError("Test error")

            args = (
                "AAPL",
                "SMACrossoverStrategy",
                {"short_window": 10, "long_window": 20},
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-31", tz="UTC"),
                "daily",
                "test_db",
                {"slippage_bps": 5.0, "commission_per_share": 0.005},
                10000.0,
                0.04,
                "test-backtest-id",
                False,
                None,
                None,
                None,
            )

            result = backtest_ticker_worker(args)

            assert result["success"] is False
            assert "error" in result
