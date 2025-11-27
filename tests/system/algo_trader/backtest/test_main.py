"""Unit and E2E tests for backtest CLI main entry point.

Tests cover argument parsing, strategy creation, ticker resolution, date validation,
and complete CLI workflows. All external dependencies are mocked via conftest.py.
E2E tests use 'debug' database for InfluxDB operations.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.backtest.main import create_strategy, main, parse_args
from system.algo_trader.strategy.strategy import Side


class TestParseArgs:
    """Test argument parsing functionality."""

    @pytest.mark.unit
    def test_parse_args_all_options(self):
        """Test parsing all command-line options."""
        test_args = [
            "--tickers",
            "AAPL",
            "MSFT",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "--database",
            "test_db",
            "--step-frequency",
            "daily",
            "--walk-forward",
            "--train-days",
            "90",
            "--test-days",
            "30",
            "--slippage-bps",
            "10.0",
            "--commission",
            "0.01",
            "--capital",
            "20000.0",
            "--account-value",
            "50000.0",
            "--trade-percentage",
            "0.15",
            "--risk-free-rate",
            "0.05",
            "--max-processes",
            "4",
            "--no-multiprocessing",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        # Mock sys.argv for testing
        with patch.object(sys, "argv", ["backtest", *test_args]):
            args = parse_args()

            assert args.tickers == ["AAPL", "MSFT"]
            assert args.start_date == "2024-01-01"
            assert args.end_date == "2024-01-31"
            assert args.database == "test_db"
            assert args.step_frequency == "daily"
            assert args.walk_forward is True
            assert args.train_days == 90
            assert args.test_days == 30
            assert args.slippage_bps == 10.0
            assert args.commission == 0.01  # Matches --commission value passed in test_args
            assert args.capital == 20000.0
            assert args.account_value == 50000.0
            assert args.trade_percentage == 0.15
            assert args.risk_free_rate == 0.05
            assert args.max_processes == 4
            assert args.no_multiprocessing is True
            assert args.strategy == "sma-crossover"
            assert args.short == 10
            assert args.long == 20

    @pytest.mark.unit
    def test_parse_args_defaults(self):
        """Test parsing with default values."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["backtest", *test_args]):
            args = parse_args()

            assert args.database == "ohlcv"
            assert args.step_frequency == "auto"
            assert args.walk_forward is False
            assert args.slippage_bps == 5.0
            assert args.commission == 0.005
            assert args.capital == 10000.0
            assert args.account_value == 10000.0
            assert args.trade_percentage == 0.10
            assert args.risk_free_rate == 0.04
            assert args.max_processes is None
            assert args.no_multiprocessing is False

    @pytest.mark.unit
    def test_parse_args_missing_required(self):
        """Test parsing fails with missing required arguments."""
        test_args = [
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["backtest", *test_args]):
            with pytest.raises(SystemExit):
                parse_args()

    @pytest.mark.unit
    def test_parse_args_strategy_required(self):
        """Test parsing requires strategy subcommand."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
        ]

        with patch.object(sys, "argv", ["backtest", *test_args]):
            with pytest.raises(SystemExit):
                parse_args()


class TestCreateStrategy:
    """Test strategy creation functionality."""

    @pytest.mark.unit
    def test_create_strategy_sma_crossover(self, mock_logger):
        """Test creating SMA crossover strategy."""
        args = MagicMock()
        args.strategy = "sma-crossover"
        args.short = 10
        args.long = 20
        args.window = 120
        args.side = "LONG"

        with patch("system.algo_trader.backtest.main.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_strategy = MagicMock()
            mock_registry.create_strategy.return_value = mock_strategy
            mock_get_registry.return_value = mock_registry

            result = create_strategy(args, mock_logger)

            assert result == mock_strategy
            mock_registry.create_strategy.assert_called_once_with(
                "sma-crossover", args, mock_logger
            )

    @pytest.mark.unit
    def test_create_strategy_unknown_strategy(self, mock_logger):
        """Test creating unknown strategy raises ValueError."""
        args = MagicMock()
        args.strategy = "unknown-strategy"

        with pytest.raises(ValueError, match="Unknown strategy"):
            create_strategy(args, mock_logger)


class TestMainTickerResolution:
    """Test ticker resolution in main function."""

    @pytest.mark.unit
    def test_resolve_tickers_specific(self, mock_logger):
        """Test resolving specific tickers."""
        test_args = [
            "--tickers",
            "AAPL",
            "MSFT",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor,
        ):
            mock_resolve.return_value = ["AAPL", "MSFT"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance

            result = main()

            assert result == 0
            # main() creates its own logger, so check tickers only
            mock_resolve.assert_called_once()
            assert mock_resolve.call_args[0][0] == ["AAPL", "MSFT"]

    @pytest.mark.unit
    def test_resolve_tickers_sp500(self, mock_logger):
        """Test resolving SP500 tickers."""
        test_args = [
            "--tickers",
            "SP500",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor,
        ):
            mock_resolve.return_value = ["AAPL", "MSFT", "GOOGL"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance

            result = main()

            assert result == 0
            # main() creates its own logger, so check tickers only
            mock_resolve.assert_called_once()
            assert mock_resolve.call_args[0][0] == ["SP500"]

    @pytest.mark.unit
    def test_resolve_tickers_failure(self, mock_logger):
        """Test handling ticker resolution failure."""
        test_args = [
            "--tickers",
            "INVALID",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
        ):
            mock_resolve.side_effect = ValueError("Failed to resolve tickers")

            result = main()

            assert result == 1


class TestMainDateValidation:
    """Test date validation in main function."""

    @pytest.mark.unit
    def test_invalid_date_format(self, mock_logger):
        """Test handling invalid date format."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "invalid-date",
            "--end-date",
            "2024-01-31",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
        ):
            mock_resolve.return_value = ["AAPL"]

            result = main()

            assert result == 1

    @pytest.mark.unit
    def test_start_date_after_end_date(self, mock_logger):
        """Test handling start date after end date."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-31",
            "--end-date",
            "2024-01-01",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
        ):
            mock_resolve.return_value = ["AAPL"]

            result = main()

            assert result == 1

    @pytest.mark.unit
    def test_valid_dates(self, mock_logger):
        """Test valid date parsing."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor,
        ):
            mock_resolve.return_value = ["AAPL"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor.return_value = mock_processor_instance

            result = main()

            assert result == 0


class TestMainExecution:
    """Test main execution workflow."""

    @pytest.mark.e2e
    def test_main_complete_workflow(self, mock_logger):
        """Test complete CLI workflow: parse → resolve → create → process."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "--database",
            "debug",  # Use debug database for E2E
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor_class,
            patch("system.algo_trader.backtest.main.get_backtest_database") as mock_get_db,
            patch("system.algo_trader.backtest.main.uuid4") as mock_uuid,
        ):
            mock_resolve.return_value = ["AAPL"]
            mock_strategy = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance
            mock_get_db.return_value = "debug"
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__ = lambda x: "test-backtest-id"

            result = main()

            assert result == 0
            mock_resolve.assert_called_once()
            mock_create.assert_called_once()
            mock_processor_instance.process_tickers.assert_called_once()

    @pytest.mark.e2e
    def test_main_walk_forward_workflow(self, mock_logger):
        """Test walk-forward analysis workflow."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-12-31",
            "--database",
            "debug",
            "--walk-forward",
            "--train-days",
            "90",
            "--test-days",
            "30",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor_class,
            patch("system.algo_trader.backtest.main.get_backtest_database") as mock_get_db,
            patch("system.algo_trader.backtest.main.uuid4") as mock_uuid,
        ):
            mock_resolve.return_value = ["AAPL"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance
            mock_get_db.return_value = "debug"
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__ = lambda x: "test-backtest-id"

            result = main()

            assert result == 0
            call_args = mock_processor_instance.process_tickers.call_args
            assert call_args[1]["walk_forward"] is True
            assert call_args[1]["train_days"] == 90
            assert call_args[1]["test_days"] == 30

    @pytest.mark.e2e
    def test_main_multiprocessing_mode(self, mock_logger):
        """Test multiprocessing mode workflow."""
        test_args = [
            "--tickers",
            "AAPL",
            "MSFT",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "--database",
            "debug",
            "--max-processes",
            "4",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor_class,
            patch("system.algo_trader.backtest.main.get_backtest_database") as mock_get_db,
            patch("system.algo_trader.backtest.main.uuid4") as mock_uuid,
        ):
            mock_resolve.return_value = ["AAPL", "MSFT"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance
            mock_get_db.return_value = "debug"
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__ = lambda x: "test-backtest-id"

            result = main()

            assert result == 0
            call_args = mock_processor_instance.process_tickers.call_args
            assert call_args[1]["use_multiprocessing"] is True
            assert call_args[1]["max_processes"] == 4

    @pytest.mark.e2e
    def test_main_sequential_mode(self, mock_logger):
        """Test sequential mode workflow."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "--database",
            "debug",
            "--no-multiprocessing",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor_class,
            patch("system.algo_trader.backtest.main.get_backtest_database") as mock_get_db,
            patch("system.algo_trader.backtest.main.uuid4") as mock_uuid,
        ):
            mock_resolve.return_value = ["AAPL"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance
            mock_get_db.return_value = "debug"
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__ = lambda x: "test-backtest-id"

            result = main()

            assert result == 0
            call_args = mock_processor_instance.process_tickers.call_args
            assert call_args[1]["use_multiprocessing"] is False

    @pytest.mark.e2e
    def test_main_account_tracking(self, mock_logger):
        """Test account value tracking workflow."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "--database",
            "debug",
            "--account-value",
            "50000.0",
            "--trade-percentage",
            "0.15",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor_class,
            patch("system.algo_trader.backtest.main.get_backtest_database") as mock_get_db,
            patch("system.algo_trader.backtest.main.uuid4") as mock_uuid,
        ):
            mock_resolve.return_value = ["AAPL"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance
            mock_get_db.return_value = "debug"
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__ = lambda x: "test-backtest-id"

            result = main()

            assert result == 0
            call_args = mock_processor_instance.process_tickers.call_args
            assert call_args[1]["initial_account_value"] == 50000.0
            assert call_args[1]["trade_percentage"] == 0.15

    @pytest.mark.unit
    def test_main_exception_handling(self, mock_logger):
        """Test exception handling in main."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor_class,
        ):
            mock_resolve.return_value = ["AAPL"]
            mock_strategy = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor_instance.process_tickers.side_effect = Exception("Processing error")
            mock_processor_class.return_value = mock_processor_instance

            result = main()

            assert result == 1

    @pytest.mark.e2e
    def test_main_with_position_manager(self, mock_logger):
        """Test complete workflow with position_manager config."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "--database",
            "debug",
            "--position-manager",
            "default",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor_class,
            patch("system.algo_trader.backtest.main.get_backtest_database") as mock_get_db,
            patch("system.algo_trader.backtest.main.uuid4") as mock_uuid,
        ):
            mock_resolve.return_value = ["AAPL"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance
            mock_get_db.return_value = "debug"
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__ = lambda x: "test-backtest-id"

            result = main()

            assert result == 0
            call_args = mock_processor_instance.process_tickers.call_args
            assert call_args[1]["position_manager_config_name"] == "default"

    @pytest.mark.e2e
    def test_main_with_position_manager_none(self, mock_logger):
        """Test workflow when position_manager config is None."""
        test_args = [
            "--tickers",
            "AAPL",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "--database",
            "debug",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with (
            patch.object(sys, "argv", ["backtest", *test_args]),
            patch("system.algo_trader.backtest.main.resolve_tickers") as mock_resolve,
            patch("system.algo_trader.backtest.main.create_strategy") as mock_create,
            patch("system.algo_trader.backtest.main.BacktestProcessor") as mock_processor_class,
            patch("system.algo_trader.backtest.main.get_backtest_database") as mock_get_db,
            patch("system.algo_trader.backtest.main.uuid4") as mock_uuid,
        ):
            mock_resolve.return_value = ["AAPL"]
            mock_strategy = MagicMock()
            mock_strategy.close = MagicMock()
            mock_create.return_value = mock_strategy
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance
            mock_get_db.return_value = "debug"
            mock_uuid.return_value = MagicMock()
            mock_uuid.return_value.__str__ = lambda x: "test-backtest-id"

            result = main()

            assert result == 0
            call_args = mock_processor_instance.process_tickers.call_args
            assert call_args[1]["position_manager_config_name"] is None
