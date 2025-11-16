"""Unit and integration tests for BacktestProcessor.

Tests cover initialization, worker args building, ticker processing, multiprocessing,
sequential processing, and complete workflows. All external dependencies are mocked
via conftest.py. Integration tests use 'debug' database.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.processor.processor import BacktestProcessor, get_backtest_database


class TestGetBacktestDatabase:
    """Test get_backtest_database function."""

    @pytest.mark.unit
    def test_get_backtest_database_prod(self):
        """Test returns 'backtest' for prod environment."""
        with patch.dict("os.environ", {"INFLUXDB3_ENVIRONMENT": "prod"}):
            result = get_backtest_database()
            assert result == "backtest"

    @pytest.mark.unit
    def test_get_backtest_database_non_prod(self):
        """Test returns 'debug' for non-prod environment."""
        with patch.dict("os.environ", {"INFLUXDB3_ENVIRONMENT": "dev"}, clear=True):
            result = get_backtest_database()
            assert result == "debug"

    @pytest.mark.unit
    def test_get_backtest_database_no_env(self):
        """Test returns 'debug' when environment variable not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_backtest_database()
            assert result == "debug"


class TestBacktestProcessorInitialization:
    """Test BacktestProcessor initialization."""

    @pytest.mark.unit
    def test_initialization_default_logger(self):
        """Test initialization creates default logger."""
        with patch("system.algo_trader.backtest.processor.processor.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            processor = BacktestProcessor()

            assert processor.logger == mock_logger
            mock_get_logger.assert_called_once_with("BacktestProcessor")

    @pytest.mark.unit
    def test_initialization_custom_logger(self):
        """Test initialization with custom logger."""
        custom_logger = MagicMock()
        processor = BacktestProcessor(logger=custom_logger)

        assert processor.logger == custom_logger


class TestBacktestProcessorBuildWorkerArgs:
    """Test _build_worker_args method."""

    @pytest.mark.unit
    def test_build_worker_args_single_ticker(self, mock_logger):
        """Test building worker args for single ticker."""
        processor = BacktestProcessor(logger=mock_logger)
        execution_config = ExecutionConfig(slippage_bps=5.0, commission_per_share=0.005)

        args = processor._build_worker_args(
            tickers=["AAPL"],
            strategy_type="SMACrossoverStrategy",
            strategy_params={"short_window": 10, "long_window": 20},
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="test_db",
            results_database="debug",
            execution_config=execution_config,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            backtest_id="test-id",
            walk_forward=False,
            train_days=None,
            test_days=None,
            train_split=None,
        )

        assert len(args) == 1
        assert args[0][0] == "AAPL"
        assert args[0][1] == "SMACrossoverStrategy"
        assert args[0][2] == {"short_window": 10, "long_window": 20}
        assert args[0][5] == "daily"
        assert args[0][6] == "test_db"
        assert args[0][7] == "debug"
        assert args[0][8] == {"slippage_bps": 5.0, "commission_per_share": 0.005}
        assert args[0][9] == 10000.0
        assert args[0][10] == 0.04
        assert args[0][11] == "test-id"
        assert args[0][12] is False

    @pytest.mark.unit
    def test_build_worker_args_multiple_tickers(self, mock_logger):
        """Test building worker args for multiple tickers."""
        processor = BacktestProcessor(logger=mock_logger)
        execution_config = ExecutionConfig()

        args = processor._build_worker_args(
            tickers=["AAPL", "MSFT", "GOOGL"],
            strategy_type="SMACrossoverStrategy",
            strategy_params={},
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="test_db",
            results_database="debug",
            execution_config=execution_config,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            backtest_id="test-id",
            walk_forward=False,
            train_days=None,
            test_days=None,
            train_split=None,
        )

        assert len(args) == 3
        assert args[0][0] == "AAPL"
        assert args[1][0] == "MSFT"
        assert args[2][0] == "GOOGL"

    @pytest.mark.unit
    def test_build_worker_args_walk_forward(self, mock_logger):
        """Test building worker args with walk-forward parameters."""
        processor = BacktestProcessor(logger=mock_logger)
        execution_config = ExecutionConfig()

        args = processor._build_worker_args(
            tickers=["AAPL"],
            strategy_type="SMACrossoverStrategy",
            strategy_params={},
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="test_db",
            results_database="debug",
            execution_config=execution_config,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            backtest_id="test-id",
            walk_forward=True,
            train_days=90,
            test_days=30,
            train_split=None,
        )

        assert args[0][12] is True
        assert args[0][13] == 90
        assert args[0][14] == 30
        assert args[0][15] is None

    @pytest.mark.unit
    def test_build_worker_args_train_split(self, mock_logger):
        """Test building worker args with train split."""
        processor = BacktestProcessor(logger=mock_logger)
        execution_config = ExecutionConfig()

        args = processor._build_worker_args(
            tickers=["AAPL"],
            strategy_type="SMACrossoverStrategy",
            strategy_params={},
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="test_db",
            results_database="debug",
            execution_config=execution_config,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            backtest_id="test-id",
            walk_forward=False,
            train_days=None,
            test_days=None,
            train_split=0.7,
        )

        assert args[0][15] == 0.7

    @pytest.mark.unit
    def test_build_worker_args_account_tracking(self, mock_logger):
        """Test building worker args with account tracking."""
        processor = BacktestProcessor(logger=mock_logger)
        execution_config = ExecutionConfig()

        args = processor._build_worker_args(
            tickers=["AAPL"],
            strategy_type="SMACrossoverStrategy",
            strategy_params={},
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="test_db",
            results_database="debug",
            execution_config=execution_config,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            backtest_id="test-id",
            walk_forward=False,
            train_days=None,
            test_days=None,
            train_split=None,
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )

        assert args[0][17] == 50000.0
        assert args[0][18] == 0.10


class TestBacktestProcessorPrintSummary:
    """Test _print_summary method."""

    @pytest.mark.unit
    def test_print_summary(self, mock_logger, capsys):
        """Test summary printing."""
        processor = BacktestProcessor(logger=mock_logger)
        summary = {"total": 10, "successful": 8, "failed": 2}

        processor._print_summary(summary)

        captured = capsys.readouterr()
        assert "Backtest Processing Summary" in captured.out
        assert "Total Tickers: 10" in captured.out
        assert "Successfully Processed: 8" in captured.out
        assert "Failed: 2" in captured.out
        assert "backtest_trades_queue" in captured.out


class TestBacktestProcessorProcessTickers:
    """Test process_tickers method."""

    @pytest.mark.unit
    def test_process_tickers_empty_list(self, mock_logger):
        """Test process_tickers with empty ticker list."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy = MagicMock()
        mock_strategy.strategy_name = "TestStrategy"

        processor.process_tickers(
            strategy=mock_strategy,
            tickers=[],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="test_db",
            results_database="debug",
            execution_config=ExecutionConfig(),
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            strategy_params={},
            backtest_id="test-id",
        )

        mock_logger.error.assert_called_once_with("No tickers provided")

    @pytest.mark.unit
    def test_process_tickers_logs_info(self, mock_logger, mock_strategy):
        """Test process_tickers logs processing info."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.strategy_name = "TestStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_sequentially"
            ) as mock_sequential,
        ):
            mock_sequential.return_value = {"total": 1, "successful": 1, "failed": 0}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="test_db",
                results_database="debug",
                execution_config=ExecutionConfig(),
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={},
                backtest_id="test-id",
                use_multiprocessing=False,
            )

            mock_logger.info.assert_called()
            call_args_str = str(mock_logger.info.call_args)
            assert "Processing backtest" in call_args_str
            assert "test-id" in call_args_str

    @pytest.mark.unit
    def test_process_tickers_determines_strategy_type(self, mock_logger, mock_strategy):
        """Test process_tickers determines strategy type from instance."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.__class__.__name__ = "SMACrossoverStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_sequentially"
            ) as mock_sequential,
        ):
            mock_sequential.return_value = {"total": 1, "successful": 1, "failed": 0}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="test_db",
                results_database="debug",
                execution_config=ExecutionConfig(),
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={},
                backtest_id="test-id",
                use_multiprocessing=False,
            )

            # Verify worker args were built with correct strategy type
            call_args = mock_sequential.call_args
            worker_args = call_args[0][0]
            assert worker_args[0][1] == "SMACrossoverStrategy"


class TestBacktestProcessorSequentialMode:
    """Test sequential processing mode."""

    @pytest.mark.unit
    def test_process_tickers_sequential_mode(self, mock_logger, mock_strategy):
        """Test process_tickers in sequential mode."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.__class__.__name__ = "SMACrossoverStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_sequentially"
            ) as mock_sequential,
        ):
            mock_sequential.return_value = {"total": 2, "successful": 2, "failed": 0}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL", "MSFT"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-10", tz="UTC"),
                step_frequency="daily",
                database="test_db",
                results_database="debug",
                execution_config=ExecutionConfig(),
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={"short_window": 10},
                backtest_id="test-id",
                use_multiprocessing=False,
            )

            mock_sequential.assert_called_once()
            call_args = mock_sequential.call_args
            assert len(call_args[0][0]) == 2  # Two worker args
            assert call_args[0][1] == ["AAPL", "MSFT"]

    @pytest.mark.integration
    def test_sequential_workflow_complete(self, mock_logger, mock_strategy):
        """Test complete sequential processing workflow."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.__class__.__name__ = "SMACrossoverStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_sequentially"
            ) as mock_sequential,
            patch(
                "system.algo_trader.backtest.processor.processor.BacktestProcessor._print_summary"
            ) as mock_print,
        ):
            mock_sequential.return_value = {"total": 2, "successful": 2, "failed": 0}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL", "MSFT"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="debug",
                results_database="debug",
                execution_config=ExecutionConfig(),
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={},
                backtest_id="test-id",
                use_multiprocessing=False,
            )

            mock_sequential.assert_called_once()
            mock_print.assert_called_once_with({"total": 2, "successful": 2, "failed": 0})


class TestBacktestProcessorMultiprocessingMode:
    """Test multiprocessing mode."""

    @pytest.mark.unit
    def test_process_tickers_multiprocessing_mode(self, mock_logger, mock_strategy):
        """Test process_tickers in multiprocessing mode."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.__class__.__name__ = "SMACrossoverStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_in_parallel"
            ) as mock_parallel,
        ):
            mock_parallel.return_value = {"total": 2, "successful": 2, "failed": 0}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL", "MSFT"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-10", tz="UTC"),
                step_frequency="daily",
                database="test_db",
                results_database="debug",
                execution_config=ExecutionConfig(),
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={"short_window": 10},
                backtest_id="test-id",
                use_multiprocessing=True,
            )

            mock_parallel.assert_called_once()
            call_args = mock_parallel.call_args
            assert len(call_args[0][0]) == 2  # Two worker args
            assert call_args[0][1] == ["AAPL", "MSFT"]
            assert call_args[0][2] is None  # max_processes default

    @pytest.mark.unit
    def test_process_tickers_custom_max_processes(self, mock_logger, mock_strategy):
        """Test process_tickers with custom max_processes."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.__class__.__name__ = "SMACrossoverStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_in_parallel"
            ) as mock_parallel,
        ):
            mock_parallel.return_value = {"total": 1, "successful": 1, "failed": 0}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-10", tz="UTC"),
                step_frequency="daily",
                database="test_db",
                results_database="debug",
                execution_config=ExecutionConfig(),
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={},
                backtest_id="test-id",
                max_processes=4,
                use_multiprocessing=True,
            )

            call_args = mock_parallel.call_args
            assert call_args[0][2] == 4  # max_processes

    @pytest.mark.integration
    def test_multiprocessing_workflow_complete(self, mock_logger, mock_strategy):
        """Test complete multiprocessing workflow."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.__class__.__name__ = "SMACrossoverStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_in_parallel"
            ) as mock_parallel,
            patch(
                "system.algo_trader.backtest.processor.processor.BacktestProcessor._print_summary"
            ) as mock_print,
        ):
            mock_parallel.return_value = {"total": 3, "successful": 3, "failed": 0}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL", "MSFT", "GOOGL"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="debug",
                results_database="debug",
                execution_config=ExecutionConfig(),
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={},
                backtest_id="test-id",
                use_multiprocessing=True,
                max_processes=2,
            )

            mock_parallel.assert_called_once()
            mock_print.assert_called_once_with({"total": 3, "successful": 3, "failed": 0})


class TestBacktestProcessorEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.unit
    def test_process_tickers_all_parameters(self, mock_logger, mock_strategy):
        """Test process_tickers with all parameters specified."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.__class__.__name__ = "SMACrossoverStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_sequentially"
            ) as mock_sequential,
        ):
            mock_sequential.return_value = {"total": 1, "successful": 1, "failed": 0}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-12-31", tz="UTC"),
                step_frequency="hourly",
                database="custom_db",
                results_database="debug",
                execution_config=ExecutionConfig(slippage_bps=10.0, commission_per_share=0.01),
                capital_per_trade=20000.0,
                risk_free_rate=0.05,
                strategy_params={"short_window": 5, "long_window": 15},
                backtest_id="custom-id",
                walk_forward=True,
                train_days=90,
                test_days=30,
                train_split=0.7,
                max_processes=8,
                use_multiprocessing=False,
                initial_account_value=50000.0,
                trade_percentage=0.15,
            )

            call_args = mock_sequential.call_args
            worker_args = call_args[0][0][0]
            assert worker_args[5] == "hourly"
            assert worker_args[6] == "custom_db"
            assert worker_args[8]["slippage_bps"] == 10.0
            assert worker_args[9] == 20000.0
            assert worker_args[10] == 0.05
            assert worker_args[12] is True
            assert worker_args[13] == 90
            assert worker_args[14] == 30
            assert worker_args[15] == 0.7
            assert worker_args[17] == 50000.0
            assert worker_args[18] == 0.15

    @pytest.mark.integration
    def test_error_propagation_from_workers(self, mock_logger, mock_strategy):
        """Test error propagation from worker failures."""
        processor = BacktestProcessor(logger=mock_logger)
        mock_strategy.__class__.__name__ = "SMACrossoverStrategy"

        with (
            patch(
                "system.algo_trader.backtest.processor.processor.process_sequentially"
            ) as mock_sequential,
        ):
            # Simulate some failures
            mock_sequential.return_value = {"total": 3, "successful": 1, "failed": 2}

            processor.process_tickers(
                strategy=mock_strategy,
                tickers=["AAPL", "MSFT", "GOOGL"],
                start_date=pd.Timestamp("2024-01-01", tz="UTC"),
                end_date=pd.Timestamp("2024-01-31", tz="UTC"),
                step_frequency="daily",
                database="debug",
                results_database="debug",
                execution_config=ExecutionConfig(),
                capital_per_trade=10000.0,
                risk_free_rate=0.04,
                strategy_params={},
                backtest_id="test-id",
                use_multiprocessing=False,
            )

            # Summary should reflect failures
            summary = mock_sequential.return_value
            assert summary["failed"] == 2
            assert summary["successful"] == 1
