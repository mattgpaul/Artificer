"""Unit tests for executor.py - Strategy execution orchestration.

Tests cover strategy creation, ticker processing, signal display, journal generation,
and the complete execute_strategy workflow. All external dependencies (logger,
InfluxDB, TradeJournal, SMACrossover) are mocked.
"""

from datetime import datetime, timedelta
from unittest.mock import ANY, MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.core.executor import (
    create_strategy,
    display_signals,
    execute_strategy,
    generate_journal,
    handle_empty_signals,
    run_strategy_for_tickers,
)

# All fixtures moved to conftest.py


class TestCreateStrategy:
    """Test strategy creation and initialization."""

    @patch("system.algo_trader.strategy.core.executor.SMACrossover")
    def test_create_sma_crossover_strategy(self, mock_sma_class, mock_args, mock_logger):
        """Test creating SMA crossover strategy with correct parameters."""
        mock_strategy_instance = MagicMock()
        mock_sma_class.return_value = mock_strategy_instance

        result = create_strategy(mock_args, mock_logger)

        assert result == mock_strategy_instance
        mock_sma_class.assert_called_once_with(
            short_window=10,
            long_window=20,
            database="test-database",
            use_threading=False,
            thread_config=None,
        )
        mock_logger.info.assert_called_once()

    @patch("system.algo_trader.strategy.core.executor.SMACrossover")
    def test_create_strategy_with_threading(self, mock_sma_class, mock_args, mock_logger):
        """Test strategy creation with threading enabled."""
        mock_args.threading = True
        mock_strategy_instance = MagicMock()
        mock_sma_class.return_value = mock_strategy_instance

        create_strategy(mock_args, mock_logger)

        mock_sma_class.assert_called_once_with(
            short_window=10,
            long_window=20,
            database="test-database",
            use_threading=True,
            thread_config=ANY,  # ThreadConfig instance when threading is enabled
        )

    def test_create_strategy_unknown_type(self, mock_args, mock_logger):
        """Test that unknown strategy type raises ValueError."""
        mock_args.strategy = "unknown-strategy"

        with pytest.raises(ValueError, match="Unknown strategy: unknown-strategy"):
            create_strategy(mock_args, mock_logger)


class TestRunStrategyForTickers:
    """Test ticker processing logic."""

    def test_run_single_ticker(self, mock_args, mock_logger, sample_signals):
        """Test running strategy for single ticker."""
        mock_strategy = MagicMock()
        mock_strategy.run_strategy.return_value = sample_signals.head(2)

        result = run_strategy_for_tickers(
            mock_strategy, ["AAPL"], "2024-01-01T00:00:00Z", mock_args, mock_logger
        )

        mock_strategy.run_strategy.assert_called_once_with(
            ticker="AAPL",
            start_time="2024-01-01T00:00:00Z",
            limit=None,
            write_signals=False,
        )
        assert len(result) == 2
        mock_logger.info.assert_called_once()

    def test_run_multiple_tickers(self, mock_args, mock_logger, sample_signals):
        """Test running strategy for multiple tickers."""
        mock_strategy = MagicMock()
        mock_strategy.run_strategy_multi.return_value = sample_signals

        tickers = ["AAPL", "MSFT", "GOOGL"]
        result = run_strategy_for_tickers(
            mock_strategy, tickers, "2024-01-01T00:00:00Z", mock_args, mock_logger
        )

        mock_strategy.run_strategy_multi.assert_called_once_with(
            tickers=tickers,
            start_time="2024-01-01T00:00:00Z",
            limit=None,
            write_signals=False,
        )
        assert len(result) == 4
        mock_logger.info.assert_called_once()

    def test_run_with_limit(self, mock_args, mock_logger, sample_signals):
        """Test running strategy with OHLCV limit."""
        mock_args.limit = 1000
        mock_strategy = MagicMock()
        mock_strategy.run_strategy.return_value = sample_signals.head(2)

        run_strategy_for_tickers(
            mock_strategy, ["AAPL"], "2024-01-01T00:00:00Z", mock_args, mock_logger
        )

        mock_strategy.run_strategy.assert_called_once_with(
            ticker="AAPL",
            start_time="2024-01-01T00:00:00Z",
            limit=1000,
            write_signals=False,
        )

    def test_run_with_write_enabled(self, mock_args, mock_logger, sample_signals):
        """Test running strategy with write_signals enabled."""
        mock_args.write = True
        mock_strategy = MagicMock()
        mock_strategy.run_strategy.return_value = sample_signals.head(2)

        run_strategy_for_tickers(
            mock_strategy, ["AAPL"], "2024-01-01T00:00:00Z", mock_args, mock_logger
        )

        mock_strategy.run_strategy.assert_called_once_with(
            ticker="AAPL",
            start_time="2024-01-01T00:00:00Z",
            limit=None,
            write_signals=True,
        )


class TestHandleEmptySignals:
    """Test handling of empty signals."""

    def test_handle_empty_signals_logs_warnings(self, mock_logger):
        """Test that appropriate warnings and suggestions are logged."""
        handle_empty_signals(mock_logger)

        # Verify warning and informational messages
        assert mock_logger.warning.call_count == 1
        assert mock_logger.info.call_count >= 4

        # Check specific messages
        calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Possible reasons:" in msg for msg in calls)
        assert any("bazel run" in msg for msg in calls)


class TestDisplaySignals:
    """Test signal display functionality."""

    @patch("system.algo_trader.strategy.core.executor.format_signal_summary")
    @patch("builtins.print")
    def test_display_signals_without_write(
        self, mock_print, mock_format, mock_args, mock_logger, sample_signals
    ):
        """Test displaying signals when write is disabled."""
        mock_format.return_value = "Formatted signal summary"
        mock_args.write = False

        display_signals(sample_signals, mock_args, mock_logger)

        mock_format.assert_called_once_with(sample_signals)
        mock_print.assert_called_once_with("Formatted signal summary")

        # Verify info messages
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("NOT written" in msg for msg in info_calls)
        assert any("--write flag" in msg for msg in info_calls)

    @patch("system.algo_trader.strategy.core.executor.format_signal_summary")
    @patch("builtins.print")
    def test_display_signals_with_write(
        self, mock_print, mock_format, mock_args, mock_logger, sample_signals
    ):
        """Test displaying signals when write is enabled."""
        mock_format.return_value = "Formatted signal summary"
        mock_args.write = True

        display_signals(sample_signals, mock_args, mock_logger)

        mock_format.assert_called_once_with(sample_signals)
        mock_print.assert_called_once()

        # Verify info message
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("written to InfluxDB" in msg for msg in info_calls)


class TestGenerateJournal:
    """Test trading journal generation."""

    @patch("system.algo_trader.strategy.core.executor.format_group_summary")
    @patch("system.algo_trader.strategy.core.executor.format_journal_summary")
    @patch("system.algo_trader.strategy.core.executor.TradeJournal")
    @patch("builtins.print")
    def test_generate_journal_success(
        self,
        mock_print,
        mock_journal_class,
        mock_format_summary,
        mock_format_group,
        mock_args,
        mock_logger,
        sample_signals,
    ):
        """Test successful journal generation with trades."""
        mock_journal = MagicMock()
        mock_journal_class.return_value = mock_journal

        mock_metrics = {
            "total_trades": 2,
            "total_profit": 500.0,
            "total_profit_pct": 5.0,
            "max_drawdown": -2.5,
            "sharpe_ratio": 1.8,
        }
        mock_trades = pd.DataFrame(
            {"entry_price": [150.0], "exit_price": [155.0], "gross_pnl": [500.0]}
        )
        mock_journal.generate_report.return_value = (mock_metrics, mock_trades)
        # Mock calculate_metrics for group summary (called when multiple tickers)
        mock_journal.calculate_metrics.return_value = {
            "total_trades": 2,
            "total_profit": 500.0,
            "total_profit_pct": 5.0,
            "max_drawdown": -2.5,
        }
        mock_format_summary.return_value = "Formatted journal summary"
        mock_format_group.return_value = "Formatted group summary"
        mock_strategy = MagicMock()
        mock_strategy.strategy_name = "test_strategy"
        mock_strategy.query_ohlcv.return_value = None

        generate_journal(sample_signals, mock_args, mock_logger, mock_strategy)

        # Verify TradeJournal was created for each ticker + group summary
        assert mock_journal_class.call_count == 3  # AAPL, MSFT, and group summary

        # Verify format and print calls (2 for individual tickers + 1 for group summary)
        assert mock_format_summary.call_count == 2
        assert mock_format_group.call_count == 1  # Group summary for multiple tickers
        assert mock_print.call_count >= 3  # 2 individual + 1 group summary

    @patch("system.algo_trader.strategy.core.executor.format_group_summary")
    @patch("system.algo_trader.strategy.core.executor.format_journal_summary")
    @patch("system.algo_trader.strategy.core.executor.format_trade_details")
    @patch("system.algo_trader.strategy.core.executor.TradeJournal")
    @patch("builtins.print")
    def test_generate_journal_with_detailed(
        self,
        mock_print,
        mock_journal_class,
        mock_format_details,
        mock_format_summary,
        mock_format_group,
        mock_args,
        mock_logger,
        sample_signals,
    ):
        """Test journal generation with detailed trade history."""
        mock_args.detailed = True
        mock_journal = MagicMock()
        mock_journal_class.return_value = mock_journal

        mock_metrics = {"total_trades": 1}
        mock_trades = pd.DataFrame({"entry_price": [150.0]})
        mock_journal.generate_report.return_value = (mock_metrics, mock_trades)
        # Mock calculate_metrics for group summary (called when multiple tickers)
        mock_journal.calculate_metrics.return_value = {
            "total_trades": 1,
            "total_profit": 0.0,
            "total_profit_pct": 0.0,
            "max_drawdown": 0.0,
        }

        mock_format_summary.return_value = "Summary"
        mock_format_details.return_value = "Details"
        mock_format_group.return_value = "Group Summary"
        mock_strategy = MagicMock()
        mock_strategy.strategy_name = "test_strategy"
        mock_strategy.query_ohlcv.return_value = None

        generate_journal(sample_signals, mock_args, mock_logger, mock_strategy)

        # Verify detailed format was called
        assert mock_format_details.call_count >= 2  # Per ticker + group summary
        assert mock_format_summary.call_count == 2

    @patch("builtins.print")
    def test_generate_journal_empty_signals(self, mock_print, mock_args, mock_logger):
        """Test journal generation with empty signals."""
        empty_signals = pd.DataFrame()
        mock_strategy = MagicMock()
        mock_strategy.strategy_name = "test_strategy"

        generate_journal(empty_signals, mock_args, mock_logger, mock_strategy)

        mock_logger.info.assert_called_once()
        assert mock_print.call_count == 3  # Three print calls for the "no signals" message

    @patch("system.algo_trader.strategy.core.executor.TradeJournal")
    def test_generate_journal_custom_capital(
        self, mock_journal_class, mock_args, mock_logger, sample_signals
    ):
        """Test journal generation with custom capital per trade."""
        mock_args.capital = 50000.0
        mock_args.risk_free_rate = 0.05

        mock_journal = MagicMock()
        mock_journal_class.return_value = mock_journal
        mock_journal.generate_report.return_value = (
            {
                "total_trades": 5,
                "total_profit": 1250.0,
                "total_profit_pct": 12.5,
                "max_drawdown": -5.2,
                "sharpe_ratio": 1.8,
            },
            pd.DataFrame(),
        )
        mock_strategy = MagicMock()
        mock_strategy.strategy_name = "test_strategy"
        mock_strategy.query_ohlcv.return_value = None

        generate_journal(sample_signals, mock_args, mock_logger, mock_strategy)

        # Verify TradeJournal was created with custom parameters
        journal_calls = mock_journal_class.call_args_list
        for call in journal_calls:
            assert call.kwargs["capital_per_trade"] == 50000.0
            assert call.kwargs["risk_free_rate"] == 0.05

    @patch("system.algo_trader.strategy.core.executor.format_group_summary")
    @patch("system.algo_trader.strategy.core.executor.format_journal_summary")
    @patch("system.algo_trader.strategy.core.executor.TradeJournal")
    @patch("builtins.print")
    def test_generate_journal_excludes_tickers_with_no_trades(
        self,
        mock_print,
        mock_journal_class,
        mock_format_summary,
        mock_format_group,
        mock_args,
        mock_logger,
        sample_signals,
    ):
        """Test that tickers with signals but no trades are excluded from output."""
        call_count = [0]  # Use list to allow modification in nested function

        def create_mock_journal(*args, **kwargs):
            """Create a mock journal that returns different results per ticker."""
            mock_journal = MagicMock()
            call_count[0] += 1

            # First call (AAPL) - has trades
            if call_count[0] == 1:
                mock_journal.generate_report.return_value = (
                    {"total_trades": 1, "total_profit": 500.0},
                    pd.DataFrame({"entry_price": [150.0], "exit_price": [155.0]}),
                )
            # Second call (MSFT) - no trades
            else:
                mock_journal.generate_report.return_value = (
                    {"total_trades": 0},
                    pd.DataFrame(),
                )
            return mock_journal

        mock_journal_class.side_effect = create_mock_journal
        mock_strategy = MagicMock()
        mock_strategy.strategy_name = "test_strategy"
        mock_strategy.query_ohlcv.return_value = None
        mock_format_summary.return_value = "Formatted journal summary"
        mock_format_group.return_value = "Formatted group summary"

        generate_journal(sample_signals, mock_args, mock_logger, mock_strategy)

        # Verify TradeJournal was created for both tickers + group summary
        assert mock_journal_class.call_count == 3  # AAPL, MSFT, and group summary

        # Verify format_journal_summary was only called for AAPL (has trades)
        assert mock_format_summary.call_count == 1

        # Verify group summary was generated (multiple tickers, even if only one has trades)
        assert mock_format_group.call_count == 1

        # Verify print was called twice (AAPL summary + group summary)
        assert mock_print.call_count == 2


class TestExecuteStrategy:
    """Test complete strategy execution workflow."""

    @patch("system.algo_trader.strategy.core.executor.create_strategy")
    @patch("system.algo_trader.strategy.core.executor.run_strategy_for_tickers")
    @patch("system.algo_trader.strategy.core.executor.display_signals")
    @patch("system.algo_trader.strategy.core.executor.datetime")
    def test_execute_strategy_success(
        self,
        mock_datetime,
        mock_display,
        mock_run,
        mock_create,
        mock_args,
        mock_logger,
        sample_signals,
    ):
        """Test successful strategy execution workflow."""
        # Mock datetime
        mock_now = datetime(2024, 6, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        # Mock strategy
        mock_strategy = MagicMock()
        mock_create.return_value = mock_strategy

        # Mock run result
        mock_run.return_value = sample_signals

        tickers = ["AAPL", "MSFT"]
        result = execute_strategy(mock_args, tickers, mock_logger)

        # Verify return code
        assert result == 0

        # Verify strategy creation and execution
        mock_create.assert_called_once_with(mock_args, mock_logger)
        mock_run.assert_called_once()

        # Verify display was called
        mock_display.assert_called_once()

        # Verify strategy cleanup
        mock_strategy.close.assert_called_once()

    @patch("system.algo_trader.strategy.core.executor.create_strategy")
    @patch("system.algo_trader.strategy.core.executor.run_strategy_for_tickers")
    @patch("system.algo_trader.strategy.core.executor.handle_empty_signals")
    @patch("system.algo_trader.strategy.core.executor.datetime")
    def test_execute_strategy_empty_signals(
        self,
        mock_datetime,
        mock_handle_empty,
        mock_run,
        mock_create,
        mock_args,
        mock_logger,
    ):
        """Test execution when no signals are generated."""
        mock_now = datetime(2024, 6, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        mock_strategy = MagicMock()
        mock_create.return_value = mock_strategy
        mock_run.return_value = pd.DataFrame()  # Empty signals

        result = execute_strategy(mock_args, ["AAPL"], mock_logger)

        assert result == 0
        mock_handle_empty.assert_called_once_with(mock_logger)
        mock_strategy.close.assert_called_once()

    @patch("system.algo_trader.strategy.core.executor.create_strategy")
    @patch("system.algo_trader.strategy.core.executor.run_strategy_for_tickers")
    @patch("system.algo_trader.strategy.core.executor.generate_journal")
    @patch("system.algo_trader.strategy.core.executor.display_signals")
    @patch("system.algo_trader.strategy.core.executor.datetime")
    def test_execute_strategy_with_journal(
        self,
        mock_datetime,
        mock_display,
        mock_generate_journal,
        mock_run,
        mock_create,
        mock_args,
        mock_logger,
        sample_signals,
    ):
        """Test execution with journal generation enabled."""
        mock_args.journal = True
        mock_now = datetime(2024, 6, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        mock_strategy = MagicMock()
        mock_create.return_value = mock_strategy
        mock_run.return_value = sample_signals

        result = execute_strategy(mock_args, ["AAPL"], mock_logger)

        assert result == 0
        mock_generate_journal.assert_called_once_with(
            sample_signals, mock_args, mock_logger, mock_strategy
        )
        mock_strategy.close.assert_called_once()

    @patch("system.algo_trader.strategy.core.executor.create_strategy")
    @patch("system.algo_trader.strategy.core.executor.run_strategy_for_tickers")
    @patch("system.algo_trader.strategy.core.executor.datetime")
    def test_execute_strategy_calculates_time_range(
        self, mock_datetime, mock_run, mock_create, mock_args, mock_logger, sample_signals
    ):
        """Test that time range is correctly calculated from lookback."""
        mock_args.lookback = 180
        mock_now = datetime(2024, 6, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        mock_strategy = MagicMock()
        mock_create.return_value = mock_strategy
        mock_run.return_value = sample_signals

        execute_strategy(mock_args, ["AAPL"], mock_logger)

        # Verify start_time was calculated correctly
        call_args = mock_run.call_args
        start_time_str = call_args[0][2]  # Third positional arg

        expected_start = mock_now - timedelta(days=180)
        expected_str = expected_start.strftime("%Y-%m-%dT%H:%M:%SZ")

        assert start_time_str == expected_str

    @patch("system.algo_trader.strategy.core.executor.create_strategy")
    @patch("system.algo_trader.strategy.core.executor.run_strategy_for_tickers")
    @patch("system.algo_trader.strategy.core.executor.datetime")
    def test_execute_strategy_exception_cleanup(
        self, mock_datetime, mock_run, mock_create, mock_args, mock_logger
    ):
        """Test that strategy.close() is called even on exception."""
        mock_now = datetime(2024, 6, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        mock_strategy = MagicMock()
        mock_create.return_value = mock_strategy
        mock_run.side_effect = Exception("Test exception")

        with pytest.raises(Exception, match="Test exception"):
            execute_strategy(mock_args, ["AAPL"], mock_logger)

        # Verify cleanup still happened
        mock_strategy.close.assert_called_once()

    @patch("system.algo_trader.strategy.core.executor.create_strategy")
    @patch("system.algo_trader.strategy.core.executor.run_strategy_for_tickers")
    @patch("system.algo_trader.strategy.core.executor.datetime")
    def test_execute_strategy_logs_configuration(
        self, mock_datetime, mock_run, mock_create, mock_args, mock_logger, sample_signals
    ):
        """Test that execution configuration is logged."""
        mock_now = datetime(2024, 6, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        mock_strategy = MagicMock()
        mock_create.return_value = mock_strategy
        mock_run.return_value = sample_signals

        execute_strategy(mock_args, ["AAPL", "MSFT"], mock_logger)

        # Verify configuration logging
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Strategy:" in msg for msg in info_calls)
        assert any("Tickers:" in msg for msg in info_calls)
        assert any("Time range:" in msg for msg in info_calls)
        assert any("Threading:" in msg for msg in info_calls)
        assert any("Database:" in msg for msg in info_calls)
        assert any("Write to DB:" in msg for msg in info_calls)
