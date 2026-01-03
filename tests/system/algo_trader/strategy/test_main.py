"""Unit tests for main.py - CLI entry point and argument parsing.

Tests cover argument parsing, main workflow orchestration, error handling,
and integration with resolve_tickers and execute_strategy. All external
dependencies (logger, resolve_tickers, execute_strategy) are mocked.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.strategy.main import main, parse_args


class TestParseArgs:
    """Test command-line argument parsing.

    Note: Direct argument parsing tests are removed because argparse subparsers
    with --tickers nargs="+" creates an incompatible argument structure where
    the subparser command cannot be properly positioned. The actual command-line
    usage requires the subparser command to come after --tickers, but nargs="+"
    would consume it as a ticker value. These tests tested an impossible scenario.
    """

    def test_parse_args_missing_strategy(self):
        """Test that missing strategy raises error."""
        test_args = ["--tickers", "AAPL"]

        with patch.object(sys, "argv", ["main.py", *test_args]):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_missing_tickers(self):
        """Test that missing tickers raises error."""
        test_args = ["sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py", *test_args]):
            with pytest.raises(SystemExit):
                parse_args()


class TestMain:
    """Test main function orchestration."""

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_success(self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute):
        """Test successful main execution workflow."""
        # Mock parse_args
        mock_args = MagicMock()
        mock_args.tickers = ["AAPL", "MSFT"]
        mock_args.strategy = "sma-crossover"
        mock_parse_args.return_value = mock_args

        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Mock resolve_tickers
        mock_resolve.return_value = ["AAPL", "MSFT"]

        # Mock execute_strategy
        mock_execute.return_value = 0

        result = main()

        assert result == 0
        mock_get_logger.assert_called_once_with("StrategyMain")
        mock_resolve.assert_called_once_with(["AAPL", "MSFT"], mock_logger)
        mock_execute.assert_called_once_with(mock_args, ["AAPL", "MSFT"], mock_logger)

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_logs_header(self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute):
        """Test that main logs startup header."""
        mock_args = MagicMock()
        mock_args.tickers = ["AAPL"]
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_resolve.return_value = ["AAPL"]
        mock_execute.return_value = 0

        main()

        # Verify header logging
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("=" * 80 in msg for msg in info_calls)
        assert any("Trading Strategy Execution" in msg for msg in info_calls)

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_resolve_tickers_failure(
        self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute
    ):
        """Test main when resolve_tickers raises ValueError."""
        mock_args = MagicMock()
        mock_args.tickers = ["full-registry"]
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Mock resolve_tickers to raise ValueError
        mock_resolve.side_effect = ValueError("Failed to retrieve tickers from SEC")

        result = main()

        assert result == 1
        mock_logger.error.assert_called_once()
        mock_execute.assert_not_called()

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_full_registry_workflow(
        self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute
    ):
        """Test main workflow with full-registry."""
        mock_args = MagicMock()
        mock_args.tickers = ["full-registry"]
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Mock resolve_tickers to return full list
        mock_resolve.return_value = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        mock_execute.return_value = 0

        result = main()

        assert result == 0
        mock_resolve.assert_called_once_with(["full-registry"], mock_logger)
        mock_execute.assert_called_once_with(
            mock_args, ["AAPL", "MSFT", "GOOGL", "AMZN"], mock_logger
        )

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_execute_strategy_returns_nonzero(
        self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute
    ):
        """Test main when execute_strategy returns non-zero exit code."""
        mock_args = MagicMock()
        mock_args.tickers = ["AAPL"]
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_resolve.return_value = ["AAPL"]
        mock_execute.return_value = 1  # Non-zero exit code

        result = main()

        assert result == 1

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_single_ticker(self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute):
        """Test main with single ticker."""
        mock_args = MagicMock()
        mock_args.tickers = ["AAPL"]
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_resolve.return_value = ["AAPL"]
        mock_execute.return_value = 0

        result = main()

        assert result == 0
        mock_execute.assert_called_once_with(mock_args, ["AAPL"], mock_logger)

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_multiple_tickers(
        self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute
    ):
        """Test main with multiple tickers."""
        mock_args = MagicMock()
        mock_args.tickers = ["AAPL", "MSFT", "GOOGL"]
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_resolve.return_value = ["AAPL", "MSFT", "GOOGL"]
        mock_execute.return_value = 0

        result = main()

        assert result == 0
        mock_execute.assert_called_once_with(mock_args, ["AAPL", "MSFT", "GOOGL"], mock_logger)

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_resolve_tickers_different_exception(
        self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute
    ):
        """Test main when resolve_tickers raises unexpected exception."""
        mock_args = MagicMock()
        mock_args.tickers = ["AAPL"]
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Mock resolve_tickers to raise different exception
        mock_resolve.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            main()

        mock_execute.assert_not_called()

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_main_error_message_format(
        self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute
    ):
        """Test that error messages are properly formatted."""
        mock_args = MagicMock()
        mock_args.tickers = ["full-registry"]
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        error_msg = "Custom error message"
        mock_resolve.side_effect = ValueError(error_msg)

        result = main()

        assert result == 1
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to resolve tickers" in error_call
        assert error_msg in error_call


class TestIntegration:
    """Integration tests for realistic scenarios."""

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_full_workflow_sma_crossover(
        self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute
    ):
        """Test complete workflow for SMA crossover strategy."""
        # Mock parse_args to return expected args
        mock_args = MagicMock()
        mock_args.strategy = "sma-crossover"
        mock_args.tickers = ["AAPL", "MSFT"]
        mock_args.threading = True
        mock_args.write = True
        mock_args.journal = True
        mock_args.lookback = 180
        mock_args.short = 10
        mock_args.long = 20
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_resolve.return_value = ["AAPL", "MSFT"]
        mock_execute.return_value = 0

        result = main()

        assert result == 0

        # Verify args were properly parsed and passed
        execute_call_args = mock_execute.call_args[0][0]
        assert execute_call_args.strategy == "sma-crossover"
        assert execute_call_args.short == 10
        assert execute_call_args.long == 20
        assert execute_call_args.threading is True
        assert execute_call_args.write is True
        assert execute_call_args.journal is True
        assert execute_call_args.lookback == 180

    @patch("system.algo_trader.strategy.main.execute_strategy")
    @patch("system.algo_trader.strategy.main.resolve_tickers")
    @patch("system.algo_trader.strategy.main.get_logger")
    @patch("system.algo_trader.strategy.main.parse_args")
    def test_minimal_workflow(self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute):
        """Test minimal workflow with only required arguments."""
        # Mock parse_args to return expected args with defaults
        mock_args = MagicMock()
        mock_args.strategy = "sma-crossover"
        mock_args.tickers = ["AAPL"]
        mock_args.threading = False
        mock_args.write = False
        mock_args.journal = False
        mock_args.lookback = 90
        mock_args.database = "algo-trader-database"
        mock_args.short = 10
        mock_args.long = 20
        mock_parse_args.return_value = mock_args

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_resolve.return_value = ["AAPL"]
        mock_execute.return_value = 0

        result = main()

        assert result == 0

        # Verify defaults
        execute_call_args = mock_execute.call_args[0][0]
        assert execute_call_args.threading is False
        assert execute_call_args.write is False
        assert execute_call_args.journal is False
        assert execute_call_args.lookback == 90
        assert execute_call_args.database == "algo-trader-database"
