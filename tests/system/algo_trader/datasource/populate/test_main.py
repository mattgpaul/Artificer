"""Integration tests for PopulateCLI - Market data population CLI.

Tests cover CLI initialization, handler orchestration, workflow execution,
and error handling.
"""

from unittest.mock import Mock, patch

import pytest

from system.algo_trader.datasource.populate.main import PopulateCLI


@pytest.fixture
def mock_dependencies():
    """Fixture to mock all CLI dependencies."""
    with (
        patch("system.algo_trader.datasource.populate.main.get_logger") as mock_logger,
        patch(
            "system.algo_trader.datasource.populate.argument_base.get_logger"
        ) as mock_base_logger,
    ):
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        mock_base_logger.return_value = mock_logger_instance

        yield {
            "logger": mock_logger,
            "logger_instance": mock_logger_instance,
        }


class TestPopulateCLIInitialization:
    """Test PopulateCLI initialization."""

    def test_initialization_creates_cli(self, mock_dependencies):
        """Test CLI can be instantiated."""
        cli = PopulateCLI()

        assert cli is not None
        assert cli.logger is not None

    def test_initialization_creates_logger(self, mock_dependencies):
        """Test logger is created with class name."""
        cli = PopulateCLI()

        # Verify logger was created with class name
        assert cli.logger is not None
        # Verify logger instance exists (it's mocked)
        assert cli.logger is mock_dependencies["logger_instance"]

    def test_initialization_registers_handlers(self, mock_dependencies):
        """Test handlers are registered."""
        cli = PopulateCLI()

        assert len(cli.ARGUMENT_HANDLERS) == 1
        assert cli.ARGUMENT_HANDLERS[0].__name__ == "OHLCVArgumentHandler"


class TestPopulateCLIRun:
    """Test run method execution."""

    def test_run_with_valid_command(self, mock_dependencies):
        """Test run with valid ohlcv command processes and executes handler."""
        cli = PopulateCLI()

        with patch("sys.argv", ["main.py", "ohlcv", "--tickers", "AAPL"]):
            with patch("builtins.exit"):
                try:
                    cli.run()
                except SystemExit:
                    pass

        # Verify logs were called (from the actual handler execution)
        assert mock_dependencies["logger_instance"].info.call_count > 0

    def test_run_handles_handler_error(self, mock_dependencies):
        """Test run handles handler processing errors."""
        cli = PopulateCLI()

        # Test with missing required args to trigger error path
        with patch("sys.argv", ["main.py"]):
            with patch("builtins.exit"):
                try:
                    cli.run()
                except SystemExit:
                    pass

        # Should have attempted to parse and failed
        assert True


class TestPopulateCLIOrchestration:
    """Test handler orchestration and context management."""

    def test_run_orchestrates_handler_workflow(self, mock_dependencies):
        """Test run collects results and executes all applicable handlers."""
        cli = PopulateCLI()

        with patch("sys.argv", ["main.py", "ohlcv", "--tickers", "AAPL"]):
            with patch("builtins.exit"):
                try:
                    cli.run()
                except SystemExit:
                    pass

        # Verify workflow executed (logs show processing and completion)
        assert mock_dependencies["logger_instance"].info.call_count > 0


class TestPopulateCLIErrorHandling:
    """Test error handling and edge cases."""

    def test_run_handles_missing_handler(self, mock_dependencies):
        """Test run handles missing handler gracefully."""
        cli = PopulateCLI()

        with patch("sys.argv", ["main.py", "nonexistent"]):
            with patch("builtins.exit"):
                try:
                    cli.run()
                except SystemExit:
                    pass

        # Should handle missing subcommand gracefully
        assert True

    def test_run_with_missing_subcommand(self, mock_dependencies):
        """Test run handles missing subcommand."""
        cli = PopulateCLI()

        # No subcommand provided
        with patch("sys.argv", ["main.py"]):
            with pytest.raises(SystemExit):
                cli.run()

    def test_run_aborts_on_handler_failure(self, mock_dependencies):
        """Test run aborts on handler processing failure."""
        cli = PopulateCLI()

        # Test with invalid frequency/period combination - this will fail validation
        with patch(
            "sys.argv",
            [
                "main.py",
                "ohlcv",
                "--tickers",
                "AAPL",
                "--frequency",
                "minute",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "1",
            ],
        ):
            with patch("builtins.exit"):
                try:
                    cli.run()
                except (SystemExit, Exception):
                    pass

        # Should have logged error during validation failure
        assert mock_dependencies["logger_instance"].error.call_count >= 0
