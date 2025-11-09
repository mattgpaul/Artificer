"""Unit tests for main.py - CLI entry point and argument parsing.

Tests cover argument parsing, main workflow orchestration, error handling,
and integration with resolve_tickers and execute_strategy. All external
dependencies (logger, resolve_tickers, execute_strategy) are mocked.
"""

import sys
from unittest.mock import MagicMock, call, patch

import pytest

from system.algo_trader.strategy.main import main, parse_args


class TestParseArgs:
    """Test command-line argument parsing."""

    def test_parse_args_minimal_required(self):
        """Test parsing with minimal required arguments."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.tickers == ["AAPL"]
        assert args.strategy == "sma-crossover"
        assert args.short == 10
        assert args.long == 20

    def test_parse_args_multiple_tickers(self):
        """Test parsing multiple tickers."""
        test_args = [
            "--tickers",
            "AAPL",
            "MSFT",
            "GOOGL",
            "sma-crossover",
            "--short",
            "5",
            "--long",
            "15",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.tickers == ["AAPL", "MSFT", "GOOGL"]

    def test_parse_args_full_registry(self):
        """Test parsing with full-registry option."""
        test_args = [
            "--tickers",
            "full-registry",
            "sma-crossover",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.tickers == ["full-registry"]

    def test_parse_args_with_threading(self):
        """Test parsing with threading enabled."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--threading",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.threading is True

    def test_parse_args_without_threading(self):
        """Test that threading defaults to False."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.threading is False

    def test_parse_args_custom_lookback(self):
        """Test parsing custom lookback period."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--lookback",
            "180",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.lookback == 180

    def test_parse_args_default_lookback(self):
        """Test that lookback defaults to 90."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.lookback == 90

    def test_parse_args_custom_database(self):
        """Test parsing custom database name."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--database",
            "custom-db",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.database == "custom-db"

    def test_parse_args_default_database(self):
        """Test that database defaults to algo-trader-database."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.database == "algo-trader-database"

    def test_parse_args_with_write_flag(self):
        """Test parsing with write flag enabled."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--write",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.write is True

    def test_parse_args_default_write(self):
        """Test that write defaults to False."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.write is False

    def test_parse_args_with_limit(self):
        """Test parsing with OHLCV limit."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--limit",
            "5000",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.limit == 5000

    def test_parse_args_default_limit(self):
        """Test that limit defaults to None."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.limit is None

    def test_parse_args_with_journal_flag(self):
        """Test parsing with journal flag enabled."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--journal",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.journal is True

    def test_parse_args_default_journal(self):
        """Test that journal defaults to False."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.journal is False

    def test_parse_args_custom_capital(self):
        """Test parsing custom capital per trade."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--capital",
            "50000.0",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.capital == 50000.0

    def test_parse_args_default_capital(self):
        """Test that capital defaults to 10000.0."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.capital == 10000.0

    def test_parse_args_custom_risk_free_rate(self):
        """Test parsing custom risk-free rate."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--risk-free-rate",
            "0.05",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.risk_free_rate == 0.05

    def test_parse_args_default_risk_free_rate(self):
        """Test that risk_free_rate defaults to 0.04."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.risk_free_rate == 0.04

    def test_parse_args_with_detailed_flag(self):
        """Test parsing with detailed journal flag."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--detailed",
            "--short",
            "10",
            "--long",
            "20",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.detailed is True

    def test_parse_args_default_detailed(self):
        """Test that detailed defaults to False."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.detailed is False

    def test_parse_args_all_flags_enabled(self):
        """Test parsing with all optional flags enabled."""
        test_args = [
            "--tickers",
            "AAPL",
            "MSFT",
            "sma-crossover",
            "--threading",
            "--write",
            "--journal",
            "--detailed",
            "--lookback",
            "180",
            "--database",
            "test-db",
            "--limit",
            "10000",
            "--capital",
            "25000.0",
            "--risk-free-rate",
            "0.03",
            "--short",
            "5",
            "--long",
            "15",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.tickers == ["AAPL", "MSFT"]
        assert args.threading is True
        assert args.write is True
        assert args.journal is True
        assert args.detailed is True
        assert args.lookback == 180
        assert args.database == "test-db"
        assert args.limit == 10000
        assert args.capital == 25000.0
        assert args.risk_free_rate == 0.03
        assert args.strategy == "sma-crossover"
        assert args.short == 5
        assert args.long == 15

    def test_parse_args_missing_strategy(self):
        """Test that missing strategy raises error."""
        test_args = ["--tickers", "AAPL"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_missing_tickers(self):
        """Test that missing tickers raises error."""
        test_args = ["sma-crossover", "--short", "10", "--long", "20"]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_sma_strategy_params(self):
        """Test SMA crossover strategy-specific parameters."""
        test_args = [
            "--tickers",
            "AAPL",
            "sma-crossover",
            "--short",
            "7",
            "--long",
            "21",
        ]

        with patch.object(sys, "argv", ["main.py"] + test_args):
            args = parse_args()

        assert args.short == 7
        assert args.long == 21


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
    def test_main_single_ticker(
        self, mock_parse_args, mock_get_logger, mock_resolve, mock_execute
    ):
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
    def test_full_workflow_sma_crossover(self, mock_get_logger, mock_resolve, mock_execute):
        """Test complete workflow for SMA crossover strategy."""
        test_args = [
            "--tickers",
            "AAPL",
            "MSFT",
            "sma-crossover",
            "--threading",
            "--write",
            "--journal",
            "--lookback",
            "180",
            "--short",
            "10",
            "--long",
            "20",
        ]

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_resolve.return_value = ["AAPL", "MSFT"]
        mock_execute.return_value = 0

        with patch.object(sys, "argv", ["main.py"] + test_args):
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
    def test_minimal_workflow(self, mock_get_logger, mock_resolve, mock_execute):
        """Test minimal workflow with only required arguments."""
        test_args = ["--tickers", "AAPL", "sma-crossover", "--short", "10", "--long", "20"]

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_resolve.return_value = ["AAPL"]
        mock_execute.return_value = 0

        with patch.object(sys, "argv", ["main.py"] + test_args):
            result = main()

        assert result == 0

        # Verify defaults
        execute_call_args = mock_execute.call_args[0][0]
        assert execute_call_args.threading is False
        assert execute_call_args.write is False
        assert execute_call_args.journal is False
        assert execute_call_args.lookback == 90
        assert execute_call_args.database == "algo-trader-database"
