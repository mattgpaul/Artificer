"""Unit and E2E tests for FundamentalsArgumentHandler.

Tests cover initialization, argument parsing, ticker resolution, bad ticker filtering,
lookback period, write flag, max threads, and complete handler workflows. All external
dependencies are mocked via conftest.py. E2E tests use 'debug' database.
"""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.datasource.populate.fundamentals.handler import (
    FundamentalsArgumentHandler,
)


class TestFundamentalsArgumentHandlerInitialization:
    """Test FundamentalsArgumentHandler initialization."""

    @pytest.mark.unit
    def test_initialization(self, mock_logger):
        """Test handler initialization."""
        handler = FundamentalsArgumentHandler()
        assert handler.name == "fundamentals"
        assert handler.logger is not None


class TestFundamentalsArgumentHandlerAddArguments:
    """Test add_arguments method."""

    @pytest.mark.unit
    def test_add_arguments_all_options(self, fundamentals_handler):
        """Test adding all argument options."""
        parser = argparse.ArgumentParser()
        fundamentals_handler.add_arguments(parser)

        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "MSFT",
                "--lookback-period",
                "15",
                "--write",
                "--max-threads",
                "8",
            ]
        )

        assert args.tickers == ["AAPL", "MSFT"]
        assert args.lookback_period == 15
        assert args.write is True
        assert args.max_threads == 8

    @pytest.mark.unit
    def test_add_arguments_defaults(self, fundamentals_handler):
        """Test argument defaults."""
        parser = argparse.ArgumentParser()
        fundamentals_handler.add_arguments(parser)

        args = parser.parse_args(["--tickers", "AAPL"])

        assert args.lookback_period == 10
        assert args.write is False
        assert args.max_threads == 4


class TestFundamentalsArgumentHandlerIsApplicable:
    """Test is_applicable method."""

    @pytest.mark.unit
    def test_is_applicable_fundamentals_command(self, fundamentals_handler):
        """Test handler applies to fundamentals command."""
        args = argparse.Namespace(command="fundamentals")
        assert fundamentals_handler.is_applicable(args) is True

    @pytest.mark.unit
    def test_is_applicable_other_command(self, fundamentals_handler):
        """Test handler does not apply to other commands."""
        args = argparse.Namespace(command="ohlcv")
        assert fundamentals_handler.is_applicable(args) is False


class TestFundamentalsArgumentHandlerProcess:
    """Test process method."""

    @pytest.mark.unit
    def test_process_specific_tickers(self, fundamentals_handler):
        """Test processing specific tickers."""
        args = argparse.Namespace(
            tickers=["AAPL", "MSFT"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        assert result["tickers"] == ["AAPL", "MSFT"]
        assert result["lookback_period"] == 10
        assert result["write"] is False
        assert result["max_threads"] == 4

    @pytest.mark.unit
    def test_process_no_tickers(self, fundamentals_handler):
        """Test processing fails without tickers."""
        args = argparse.Namespace(
            tickers=None,
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        with pytest.raises(ValueError, match="--tickers is required"):
            fundamentals_handler.process(args)

    @pytest.mark.unit
    def test_process_sp500_tickers(self, fundamentals_handler):
        """Test processing SP500 tickers."""
        args = argparse.Namespace(
            tickers=["SP500"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        with patch(
            "system.algo_trader.datasource.populate.fundamentals.handler.get_sp500_tickers"
        ) as mock_get_sp500:
            mock_get_sp500.return_value = ["AAPL", "MSFT", "GOOGL"]

            result = fundamentals_handler.process(args)

            assert len(result["tickers"]) == 3
            assert "AAPL" in result["tickers"]

    @pytest.mark.unit
    def test_process_full_registry(self, fundamentals_handler, mock_tickers):
        """Test processing full-registry tickers."""
        mock_tickers.get_tickers.return_value = {
            "key1": {"ticker": "AAPL"},
            "key2": {"ticker": "MSFT"},
        }
        args = argparse.Namespace(
            tickers=["full-registry"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        assert len(result["tickers"]) == 2
        assert "AAPL" in result["tickers"]

    @pytest.mark.unit
    def test_process_bad_ticker_filtering(self, fundamentals_handler, mock_bad_ticker_client):
        """Test bad ticker filtering when write=True."""
        mock_bad_ticker_client.is_bad_ticker.side_effect = lambda t: t == "BAD"
        args = argparse.Namespace(
            tickers=["AAPL", "BAD", "MSFT"],
            lookback_period=10,
            write=True,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        assert len(result["tickers"]) == 2
        assert "BAD" not in result["tickers"]
        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]

    @pytest.mark.unit
    def test_process_no_bad_ticker_filtering_dry_run(self, fundamentals_handler):
        """Test no bad ticker filtering in dry-run mode."""
        args = argparse.Namespace(
            tickers=["AAPL", "BAD", "MSFT"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        assert len(result["tickers"]) == 3
        assert "BAD" in result["tickers"]

    @pytest.mark.unit
    def test_process_bad_ticker_client_error(self, fundamentals_handler, mock_bad_ticker_client):
        """Test handling bad ticker client errors."""
        mock_bad_ticker_client.is_bad_ticker.side_effect = Exception("Connection error")
        args = argparse.Namespace(
            tickers=["AAPL", "MSFT"],
            lookback_period=10,
            write=True,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        # Should continue without filtering
        assert len(result["tickers"]) == 2

    @pytest.mark.unit
    def test_process_custom_lookback_period(self, fundamentals_handler):
        """Test custom lookback period."""
        args = argparse.Namespace(
            tickers=["AAPL"],
            lookback_period=15,
            write=False,
            max_threads=4,
        )

        result = fundamentals_handler.process(args)

        assert result["lookback_period"] == 15

    @pytest.mark.unit
    def test_process_custom_max_threads(self, fundamentals_handler):
        """Test custom max threads."""
        args = argparse.Namespace(
            tickers=["AAPL"],
            lookback_period=10,
            write=False,
            max_threads=8,
        )

        result = fundamentals_handler.process(args)

        assert result["max_threads"] == 8

    @pytest.mark.unit
    def test_process_sp500_failure(self, fundamentals_handler):
        """Test handling SP500 fetch failure."""
        args = argparse.Namespace(
            tickers=["SP500"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        with patch(
            "system.algo_trader.datasource.populate.fundamentals.handler.get_sp500_tickers"
        ) as mock_get_sp500:
            mock_get_sp500.return_value = []

            with pytest.raises(ValueError, match="Failed to retrieve S&P 500 tickers"):
                fundamentals_handler.process(args)

    @pytest.mark.unit
    def test_process_full_registry_failure(self, fundamentals_handler, mock_tickers):
        """Test handling full-registry fetch failure."""
        mock_tickers.get_tickers.return_value = None
        args = argparse.Namespace(
            tickers=["full-registry"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        with pytest.raises(ValueError, match="Failed to retrieve tickers from SEC"):
            fundamentals_handler.process(args)

    @pytest.mark.e2e
    def test_process_complete_workflow_dry_run(self, fundamentals_handler):
        """Test complete handler workflow in dry-run mode."""
        args = argparse.Namespace(
            tickers=["AAPL", "MSFT"],
            lookback_period=10,
            write=False,
            max_threads=4,
        )

        with patch(
            "system.algo_trader.datasource.populate.fundamentals.handler.FundamentalsProcessor"
        ) as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor

            result = fundamentals_handler.process(args)
            fundamentals_handler.execute(result)

            mock_processor_class.assert_called_once()
            mock_processor.process_tickers.assert_called_once()
            call_args = mock_processor.process_tickers.call_args
            assert call_args[0][2] is False  # write is the 3rd positional argument

    @pytest.mark.e2e
    def test_process_complete_workflow_write_mode(
        self, fundamentals_handler, mock_bad_ticker_client
    ):
        """Test complete handler workflow in write mode."""
        mock_bad_ticker_client.is_bad_ticker.return_value = False
        args = argparse.Namespace(
            tickers=["AAPL", "MSFT"],
            lookback_period=10,
            write=True,
            max_threads=4,
        )

        with patch(
            "system.algo_trader.datasource.populate.fundamentals.handler.FundamentalsProcessor"
        ) as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor

            result = fundamentals_handler.process(args)
            fundamentals_handler.execute(result)

            mock_processor.process_tickers.assert_called_once()
            call_args = mock_processor.process_tickers.call_args
            assert call_args[0][2] is True  # write is the 3rd positional argument
