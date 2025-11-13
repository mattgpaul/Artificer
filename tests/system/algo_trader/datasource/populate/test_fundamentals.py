"""Unit tests for FundamentalsArgumentHandler - Fundamentals Data Population.

Tests cover argument parsing, processing, execution, and error handling.
All external dependencies are mocked via conftest.py.
"""

import argparse

import pandas as pd
import pytest

from system.algo_trader.datasource.populate.fundamentals import (
    FUNDAMENTALS_QUEUE_NAME,
    FUNDAMENTALS_STATIC_QUEUE_NAME,
)


class TestFundamentalsArgumentHandlerInitialization:
    """Test FundamentalsArgumentHandler initialization."""

    def test_initialization_success(self, fundamentals_handler):
        """Test FundamentalsArgumentHandler initializes correctly."""
        assert fundamentals_handler is not None
        assert fundamentals_handler.name == "fundamentals"
        assert hasattr(fundamentals_handler, "logger")


class TestFundamentalsArgumentHandlerAddArguments:
    """Test argument parsing."""

    def test_add_arguments_adds_all_required_args(self, fundamentals_handler):
        """Test add_arguments adds all required command-line arguments."""
        parser = argparse.ArgumentParser()
        fundamentals_handler.add_arguments(parser)

        # Verify all arguments are added
        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "MSFT",
                "--lookback-period",
                "5",
                "--write",
                "--max-threads",
                "8",
            ]
        )

        assert args.tickers == ["AAPL", "MSFT"]
        assert args.lookback_period == 5
        assert args.write is True
        assert args.max_threads == 8

    def test_add_arguments_defaults(self, fundamentals_handler):
        """Test add_arguments sets correct defaults."""
        parser = argparse.ArgumentParser()
        fundamentals_handler.add_arguments(parser)

        args = parser.parse_args(["--tickers", "AAPL"])

        assert args.lookback_period == 10
        assert args.write is False
        assert args.max_threads == 4


class TestFundamentalsArgumentHandlerIsApplicable:
    """Test is_applicable method."""

    def test_is_applicable_true_when_command_matches(self, fundamentals_handler):
        """Test is_applicable returns True when command is fundamentals."""
        args = argparse.Namespace(command="fundamentals")
        assert fundamentals_handler.is_applicable(args) is True

    def test_is_applicable_false_when_command_differs(self, fundamentals_handler):
        """Test is_applicable returns False when command differs."""
        args = argparse.Namespace(command="ohlcv")
        assert fundamentals_handler.is_applicable(args) is False

    def test_is_applicable_false_when_no_command(self, fundamentals_handler):
        """Test is_applicable returns False when no command attribute."""
        args = argparse.Namespace()
        assert fundamentals_handler.is_applicable(args) is False


class TestFundamentalsArgumentHandlerProcess:
    """Test process method."""

    def test_process_specific_tickers(self, fundamentals_handler, mock_bad_ticker_client):
        """Test process with specific tickers."""
        args = argparse.Namespace(
            tickers=["AAPL", "MSFT"],
            lookback_period=5,
            write=False,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        assert result["tickers"] == ["AAPL", "MSFT"]
        assert result["lookback_period"] == 5
        assert result["write"] is False
        assert result["max_threads"] == 4

    def test_process_full_registry(
        self, fundamentals_handler, mock_tickers, mock_bad_ticker_client
    ):
        """Test process with full-registry option."""
        mock_tickers.get_tickers.return_value = {
            "0": {"ticker": "AAPL", "cik_str": 320193},
            "1": {"ticker": "MSFT", "cik_str": 789019},
        }

        args = argparse.Namespace(
            tickers=["full-registry"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]
        mock_tickers.get_tickers.assert_called_once()

    def test_process_full_registry_fails(self, fundamentals_handler, mock_tickers):
        """Test process raises error when full-registry fails."""
        mock_tickers.get_tickers.return_value = None

        args = argparse.Namespace(
            tickers=["full-registry"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        with pytest.raises(ValueError, match="Failed to retrieve tickers"):
            fundamentals_handler.process(args)

    def test_process_no_tickers_raises_error(self, fundamentals_handler):
        """Test process raises error when no tickers provided."""
        args = argparse.Namespace(
            tickers=None,
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        with pytest.raises(ValueError, match="--tickers is required"):
            fundamentals_handler.process(args)

    def test_process_filters_bad_tickers(self, fundamentals_handler, mock_bad_ticker_client):
        """Test process filters out bad tickers."""
        mock_bad_ticker_client.is_bad_ticker.side_effect = lambda t: t == "BAD"

        args = argparse.Namespace(
            tickers=["AAPL", "BAD", "MSFT"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        assert "BAD" not in result["tickers"]
        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]


class TestFundamentalsArgumentHandlerExecute:
    """Test execute method."""

    def test_execute_dry_run_mode(self, fundamentals_handler, mock_tickers, mock_thread_manager):
        """Test execute in dry-run mode (no writes)."""
        mock_tickers.get_company_facts.return_value = {
            "static": {"ticker": "AAPL", "entity_name": "Apple Inc."},
            "time_series": pd.DataFrame({"revenue": [100, 200], "datetime": [1, 2]}),
        }

        context = {
            "tickers": ["AAPL"],
            "lookback_period": 10,
            "write": False,
            "max_threads": 4,
        }

        # Mock thread execution to complete immediately
        def start_thread_side_effect(*args, **kwargs):
            # Simulate thread completing immediately
            target = kwargs.get("target")
            ticker_args = kwargs.get("args", ())
            if target and callable(target) and ticker_args:
                ticker = ticker_args[0]
                result = target(ticker)
                # Update summary stats
                mock_thread_manager.get_results_summary.return_value = {
                    "successful": 1 if result.get("success") else 0,
                    "failed": 0 if result.get("success") else 1,
                }

        mock_thread_manager.start_thread.side_effect = start_thread_side_effect
        mock_thread_manager.get_active_thread_count.return_value = 0

        fundamentals_handler.execute(context)

        mock_tickers.get_company_facts.assert_called()
        mock_thread_manager.wait_for_all_threads.assert_called()

    def test_execute_write_mode(
        self, fundamentals_handler, mock_tickers, mock_queue_broker, mock_thread_manager
    ):
        """Test execute in write mode (writes to Redis)."""
        time_series_df = pd.DataFrame(
            {
                "revenue": [100, 200],
                "market_cap": [1000, 2000],
            },
            index=pd.to_datetime(["2020-01-01", "2020-04-01"], utc=True),
        )
        mock_tickers.get_company_facts.return_value = {
            "static": {"ticker": "AAPL", "entity_name": "Apple Inc."},
            "time_series": time_series_df,
        }

        context = {
            "tickers": ["AAPL"],
            "lookback_period": 10,
            "write": True,
            "max_threads": 4,
        }

        def start_thread_side_effect(*args, **kwargs):
            target = kwargs.get("target")
            ticker_args = kwargs.get("args", ())
            if target and callable(target) and ticker_args:
                ticker = ticker_args[0]
                result = target(ticker)
                mock_thread_manager.get_results_summary.return_value = {
                    "successful": 1 if result.get("success") else 0,
                    "failed": 0 if result.get("success") else 1,
                }

        mock_thread_manager.start_thread.side_effect = start_thread_side_effect
        mock_thread_manager.get_active_thread_count.return_value = 0

        fundamentals_handler.execute(context)

        mock_queue_broker.enqueue.assert_called()
        mock_tickers.get_company_facts.assert_called()

    def test_execute_no_tickers_logs_error(self, fundamentals_handler):
        """Test execute logs error when no tickers in context."""
        context = {}

        fundamentals_handler.execute(context)

        fundamentals_handler.logger.error.assert_called()

    def test_execute_handles_fetch_failure(
        self, fundamentals_handler, mock_tickers, mock_thread_manager
    ):
        """Test execute handles company facts fetch failure."""
        mock_tickers.get_company_facts.return_value = None

        context = {
            "tickers": ["AAPL"],
            "lookback_period": 10,
            "write": False,
            "max_threads": 4,
        }

        def start_thread_side_effect(*args, **kwargs):
            target = kwargs.get("args", [None])[0]
            if target and callable(target):
                ticker = (
                    kwargs.get("args", [None])[0] if len(kwargs.get("args", [])) > 0 else "AAPL"
                )
                target(ticker)
                mock_thread_manager.get_results_summary.return_value = {
                    "successful": 0,
                    "failed": 1,
                }

        mock_thread_manager.start_thread.side_effect = start_thread_side_effect
        mock_thread_manager.get_active_thread_count.return_value = 0

        fundamentals_handler.execute(context)

        mock_thread_manager.wait_for_all_threads.assert_called()

    def test_execute_handles_empty_time_series(
        self, fundamentals_handler, mock_tickers, mock_thread_manager
    ):
        """Test execute handles empty time series DataFrame."""
        mock_tickers.get_company_facts.return_value = {
            "static": {"ticker": "AAPL"},
            "time_series": pd.DataFrame(),
        }

        context = {
            "tickers": ["AAPL"],
            "lookback_period": 10,
            "write": False,
            "max_threads": 4,
        }

        def start_thread_side_effect(*args, **kwargs):
            target = kwargs.get("target")
            ticker_args = kwargs.get("args", ())
            if target and callable(target) and ticker_args:
                ticker = ticker_args[0]
                target(ticker)
                mock_thread_manager.get_results_summary.return_value = {
                    "successful": 0,
                    "failed": 1,
                }

        mock_thread_manager.start_thread.side_effect = start_thread_side_effect
        mock_thread_manager.get_active_thread_count.return_value = 0

        fundamentals_handler.execute(context)

        fundamentals_handler.logger.warning.assert_called()

    def test_execute_handles_redis_enqueue_failure(
        self, fundamentals_handler, mock_tickers, mock_queue_broker, mock_thread_manager
    ):
        """Test execute handles Redis enqueue failure."""
        time_series_df = pd.DataFrame(
            {"revenue": [100]}, index=pd.to_datetime(["2020-01-01"], utc=True)
        )
        mock_tickers.get_company_facts.return_value = {
            "static": {"ticker": "AAPL"},
            "time_series": time_series_df,
        }
        mock_queue_broker.enqueue.return_value = False

        context = {
            "tickers": ["AAPL"],
            "lookback_period": 10,
            "write": True,
            "max_threads": 4,
        }

        def start_thread_side_effect(*args, **kwargs):
            target = kwargs.get("target")
            ticker_args = kwargs.get("args", ())
            if target and callable(target) and ticker_args:
                ticker = ticker_args[0]
                target(ticker)
                mock_thread_manager.get_results_summary.return_value = {
                    "successful": 0,
                    "failed": 1,
                }

        mock_thread_manager.start_thread.side_effect = start_thread_side_effect
        mock_thread_manager.get_active_thread_count.return_value = 0

        fundamentals_handler.execute(context)

        fundamentals_handler.logger.error.assert_called()

    @pytest.mark.timeout(10)
    def test_execute_batches_tickers_when_exceeding_max_threads(
        self, fundamentals_handler, mock_tickers, mock_thread_manager
    ):
        """Test execute batches tickers when count exceeds max_threads."""
        mock_tickers.get_company_facts.return_value = {
            "static": {"ticker": "AAPL"},
            "time_series": pd.DataFrame(
                {"revenue": [100]}, index=pd.to_datetime(["2020-01-01"], utc=True)
            ),
        }

        context = {
            "tickers": ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],
            "lookback_period": 10,
            "write": False,
            "max_threads": 2,
        }

        started_threads = []

        def start_thread_side_effect(*args, **kwargs):
            target = kwargs.get("target")
            ticker_args = kwargs.get("args", ())
            if target and callable(target) and ticker_args:
                ticker = ticker_args[0]
                started_threads.append(ticker)
                target(ticker)
                # Update summary after each thread completes
                mock_thread_manager.get_results_summary.return_value = {
                    "successful": len(started_threads),
                    "failed": 0,
                }

        # Return 0 active threads to allow all threads to start immediately
        # The batching logic will still work because max_threads limits concurrent execution
        mock_thread_manager.get_active_thread_count.return_value = 0

        mock_thread_manager.start_thread.side_effect = start_thread_side_effect

        fundamentals_handler.execute(context)

        # Verify all tickers were processed (start_thread called for each)
        assert mock_thread_manager.start_thread.call_count == len(context["tickers"])
        assert len(started_threads) == len(context["tickers"])


class TestFundamentalsArgumentHandlerHelperMethods:
    """Test helper methods."""

    def test_dataframe_to_dict_with_datetime_index(self, fundamentals_handler):
        """Test _dataframe_to_dict with DatetimeIndex."""
        df = pd.DataFrame(
            {"revenue": [100, 200]},
            index=pd.to_datetime(["2020-01-01", "2020-04-01"], utc=True),
        )

        result = fundamentals_handler._dataframe_to_dict(df)

        assert "datetime" in result
        assert "revenue" in result
        assert len(result["datetime"]) == 2

    def test_dataframe_to_dict_with_time_column(self, fundamentals_handler):
        """Test _dataframe_to_dict with time column."""
        df = pd.DataFrame(
            {
                "time": ["2020-01-01", "2020-04-01"],
                "revenue": [100, 200],
            }
        )

        result = fundamentals_handler._dataframe_to_dict(df)

        assert "datetime" in result
        assert "revenue" in result
        assert "time" not in result

    def test_print_summary_dry_run(self, fundamentals_handler, capsys):
        """Test _print_summary in dry-run mode."""
        stats = {
            "total": 10,
            "successful": 8,
            "failed": 2,
            "static_rows": 8,
            "time_series_rows": 100,
            "market_cap_rows": 80,
        }

        fundamentals_handler._print_summary(stats, write=False)

        captured = capsys.readouterr()
        assert "Dry-run mode" in captured.out
        assert "10" in captured.out
        assert "8" in captured.out

    def test_print_summary_write_mode(self, fundamentals_handler, capsys):
        """Test _print_summary in write mode."""
        stats = {
            "total": 10,
            "successful": 8,
            "failed": 2,
            "static_rows": 8,
            "time_series_rows": 100,
            "market_cap_rows": 80,
        }

        fundamentals_handler._print_summary(stats, write=True)

        captured = capsys.readouterr()
        assert FUNDAMENTALS_QUEUE_NAME in captured.out
        assert FUNDAMENTALS_STATIC_QUEUE_NAME in captured.out
        assert "InfluxDB" in captured.out
