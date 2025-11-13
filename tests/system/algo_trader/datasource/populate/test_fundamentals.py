"""Unit tests for FundamentalsArgumentHandler - Fundamentals Data Population.

Tests cover argument parsing, processing, execution, and error handling.
All external dependencies are mocked via conftest.py.
"""

import argparse
from unittest.mock import patch

import pandas as pd
import pytest


class TestFundamentalsArgumentHandler:
    """Test Fundamentals handler core functionality."""

    def test_initialization(self, fundamentals_handler):
        """Test handler initializes correctly."""
        assert fundamentals_handler.name == "fundamentals"
        assert fundamentals_handler.logger is not None

    def test_is_applicable(self, fundamentals_handler):
        """Test is_applicable method."""
        assert (
            fundamentals_handler.is_applicable(argparse.Namespace(command="fundamentals")) is True
        )
        assert fundamentals_handler.is_applicable(argparse.Namespace(command="other")) is False

    def test_add_arguments(self, fundamentals_handler):
        """Test all arguments are added correctly."""
        parser = argparse.ArgumentParser()
        fundamentals_handler.add_arguments(parser)

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
        """Test argument defaults."""
        parser = argparse.ArgumentParser()
        fundamentals_handler.add_arguments(parser)
        args = parser.parse_args(["--tickers", "AAPL"])

        assert args.lookback_period == 10
        assert args.write is False
        assert args.max_threads == 4

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
        # Verify Tickers was instantiated and get_tickers was called
        assert mock_tickers.get_tickers.called

    def test_process_requires_tickers(self, fundamentals_handler):
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
        """Test process filters out bad tickers when write=True."""
        mock_bad_ticker_client.is_bad_ticker.side_effect = lambda t: t == "BAD"

        args = argparse.Namespace(
            tickers=["AAPL", "BAD", "MSFT"],
            lookback_period=10,
            write=True,  # Bad ticker filtering only happens when write=True
            max_threads=4,
        )

        result = fundamentals_handler.process(args)
        assert "BAD" not in result["tickers"]
        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]

    def test_process_handles_bad_ticker_client_error(self, fundamentals_handler):
        """Test process handles BadTickerClient connection errors."""
        with patch(
            "system.algo_trader.datasource.populate.fundamentals.handler.BadTickerClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Connection error")

            args = argparse.Namespace(
                tickers=["AAPL"],
                lookback_period=10,
                write=True,
                max_threads=4,
            )

            # Should not raise, but log warning
            result = fundamentals_handler.process(args)
            assert result["tickers"] == ["AAPL"]
            fundamentals_handler.logger.warning.assert_called()

    def test_execute_dry_run_mode(self, fundamentals_handler, mock_tickers, mock_thread_manager):
        """Test execute in dry-run mode (no writes)."""
        with patch(
            "system.algo_trader.datasource.populate.fundamentals.processor.Tickers"
        ) as mock_processor_tickers:
            mock_processor_tickers.return_value = mock_tickers
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

            def start_thread_side_effect(*args, **kwargs):
                target = kwargs.get("target")
                ticker_args = kwargs.get("args", ())
                if target and callable(target) and ticker_args:
                    target(ticker_args[0])
                    mock_thread_manager.get_results_summary.return_value = {
                        "successful": 1,
                        "failed": 0,
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
        with patch(
            "system.algo_trader.datasource.populate.fundamentals.processor.Tickers"
        ) as mock_processor_tickers:
            mock_processor_tickers.return_value = mock_tickers
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
                    target(ticker_args[0])
                    mock_thread_manager.get_results_summary.return_value = {
                        "successful": 1,
                        "failed": 0,
                    }

            mock_thread_manager.start_thread.side_effect = start_thread_side_effect
            mock_thread_manager.get_active_thread_count.return_value = 0

            fundamentals_handler.execute(context)
            mock_queue_broker.enqueue.assert_called()
            mock_tickers.get_company_facts.assert_called()

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
            target = kwargs.get("target")
            ticker_args = kwargs.get("args", ())
            if target and callable(target) and ticker_args:
                target(ticker_args[0])
                mock_thread_manager.get_results_summary.return_value = {
                    "successful": 0,
                    "failed": 1,
                }

        mock_thread_manager.start_thread.side_effect = start_thread_side_effect
        mock_thread_manager.get_active_thread_count.return_value = 0

        fundamentals_handler.execute(context)
        mock_thread_manager.wait_for_all_threads.assert_called()

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
                mock_thread_manager.get_results_summary.return_value = {
                    "successful": len(started_threads),
                    "failed": 0,
                }

        mock_thread_manager.get_active_thread_count.return_value = 0
        mock_thread_manager.start_thread.side_effect = start_thread_side_effect

        fundamentals_handler.execute(context)
        assert mock_thread_manager.start_thread.call_count == len(context["tickers"])
