"""Unit tests for OHLCVArgumentHandler - OHLCV data population handler.

Tests cover initialization, argument parsing, ticker fetching, validation,
and execution logic. All external dependencies are mocked.
"""

import argparse
from unittest.mock import Mock, patch

import pytest

from system.algo_trader.datasource.populate.ohlcv_args import (
    OHLCVArgumentHandler,
)
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


@pytest.fixture
def mock_dependencies():
    """Fixture to mock all OHLCV handler dependencies."""
    with (
        patch("system.algo_trader.datasource.populate.argument_base.get_logger") as mock_logger,
        patch("system.algo_trader.datasource.populate.ohlcv_args.Tickers") as mock_tickers,
    ):
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance

        yield {
            "logger": mock_logger,
            "logger_instance": mock_logger_instance,
            "tickers": mock_tickers,
        }


class TestOHLCVArgumentHandlerInitialization:
    """Test OHLCV handler initialization."""

    def test_initialization_creates_handler(self, mock_dependencies):
        """Test handler can be instantiated."""
        handler = OHLCVArgumentHandler()

        assert handler.name == "ohlcv"
        assert handler.logger is not None

    def test_initialization_creates_logger(self, mock_dependencies):
        """Test logger is created with class name."""
        handler = OHLCVArgumentHandler()

        # Verify logger was created - it's created in base class __init__
        assert handler.logger is not None


class TestOHLCVArgumentHandlerArguments:
    """Test argument definitions."""

    @pytest.fixture
    def parser(self):
        """Create argument parser for testing."""
        return argparse.ArgumentParser()

    def test_adds_tickers_argument(self, mock_dependencies, parser):
        """Test tickers argument is added."""
        handler = OHLCVArgumentHandler()
        handler.add_arguments(parser)

        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "MSFT",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )

        assert args.tickers == ["AAPL", "MSFT"]

    def test_adds_frequency_argument(self, mock_dependencies, parser):
        """Test frequency argument is added."""
        handler = OHLCVArgumentHandler()
        handler.add_arguments(parser)

        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )

        assert args.frequency == "daily"

    def test_adds_period_argument(self, mock_dependencies, parser):
        """Test period argument is added."""
        handler = OHLCVArgumentHandler()
        handler.add_arguments(parser)

        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )

        assert args.period == "year"

    def test_adds_frequency_value_argument(self, mock_dependencies, parser):
        """Test frequency-value argument is added."""
        handler = OHLCVArgumentHandler()
        handler.add_arguments(parser)

        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )

        assert args.frequency_value == 1

    def test_adds_period_value_argument(self, mock_dependencies, parser):
        """Test period-value argument is added."""
        handler = OHLCVArgumentHandler()
        handler.add_arguments(parser)

        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )

        assert args.period_value == 10

    def test_frequency_has_choices(self, mock_dependencies, parser):
        """Test frequency argument has valid choices."""
        handler = OHLCVArgumentHandler()
        handler.add_arguments(parser)

        # Valid choice
        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )
        assert args.frequency == "daily"

        # Invalid choice should fail
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "--tickers",
                    "AAPL",
                    "--frequency",
                    "invalid",
                    "--period",
                    "year",
                    "--frequency-value",
                    "1",
                    "--period-value",
                    "10",
                ]
            )

    def test_period_has_choices(self, mock_dependencies, parser):
        """Test period argument has valid choices."""
        handler = OHLCVArgumentHandler()
        handler.add_arguments(parser)

        # Valid choice
        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )
        assert args.period == "year"

        # Invalid choice should fail
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "--tickers",
                    "AAPL",
                    "--frequency",
                    "daily",
                    "--period",
                    "invalid",
                    "--frequency-value",
                    "1",
                    "--period-value",
                    "10",
                ]
            )


class TestOHLCVArgumentHandlerApplicability:
    """Test is_applicable method."""

    def test_is_applicable_with_ohlcv_command(self, mock_dependencies):
        """Test handler is applicable when command is ohlcv."""
        handler = OHLCVArgumentHandler()

        # Create args with ohlcv command
        args = argparse.Namespace(command="ohlcv")

        assert handler.is_applicable(args) is True

    def test_not_applicable_with_different_command(self, mock_dependencies):
        """Test handler is not applicable with different command."""
        handler = OHLCVArgumentHandler()

        # Create args with different command
        args = argparse.Namespace(command="other")

        assert handler.is_applicable(args) is False


class TestOHLCVArgumentHandlerProcess:
    """Test process method."""

    def test_process_with_specific_tickers(self, mock_dependencies):
        """Test process with specific ticker list."""
        handler = OHLCVArgumentHandler()

        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)
        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "MSFT",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )

        result = handler.process(args)

        assert result["tickers"] == ["AAPL", "MSFT"]
        assert result["frequency_type"] == FrequencyType.DAILY
        assert result["frequency_value"] == 1
        assert result["period_type"] == PeriodType.YEAR
        assert result["period_value"] == 10

    def test_process_with_full_registry(self, mock_dependencies):
        """Test process with full-registry fetches all tickers."""
        handler = OHLCVArgumentHandler()

        # Mock ticker data
        mock_ticker_source = Mock()
        mock_ticker_source.get_tickers.return_value = {
            "0": {"ticker": "AAPL", "cik_str": 123},
            "1": {"ticker": "MSFT", "cik_str": 456},
        }
        mock_dependencies["tickers"].return_value = mock_ticker_source

        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)
        args = parser.parse_args(
            [
                "--tickers",
                "full-registry",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )

        result = handler.process(args)

        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]
        mock_ticker_source.get_tickers.assert_called_once()

    def test_process_validates_frequency_period_combination(self, mock_dependencies):
        """Test process validates frequency and period combinations."""
        handler = OHLCVArgumentHandler()

        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)

        # Invalid combination: minute frequency with year period
        args = parser.parse_args(
            [
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
            ]
        )

        with pytest.raises(ValueError, match="Invalid frequency type minute for year"):
            handler.process(args)

    def test_process_validates_frequency_value(self, mock_dependencies):
        """Test process validates frequency value."""
        handler = OHLCVArgumentHandler()

        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)

        # Invalid frequency value: daily should only be 1, not 5
        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "5",
                "--period-value",
                "10",
            ]
        )

        with pytest.raises(ValueError, match="Invalid frequency value"):
            handler.process(args)

    def test_process_handles_sec_fetch_failure(self, mock_dependencies):
        """Test process handles SEC fetch failure."""
        handler = OHLCVArgumentHandler()

        # Mock ticker fetch failure
        mock_ticker_source = Mock()
        mock_ticker_source.get_tickers.return_value = None
        mock_dependencies["tickers"].return_value = mock_ticker_source

        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)
        args = parser.parse_args(
            [
                "--tickers",
                "full-registry",
                "--frequency",
                "daily",
                "--period",
                "year",
                "--frequency-value",
                "1",
                "--period-value",
                "10",
            ]
        )

        with pytest.raises(ValueError, match="Failed to retrieve tickers from SEC"):
            handler.process(args)


class TestOHLCVArgumentHandlerExecute:
    """Test execute method."""

    def test_execute_with_valid_context(self, mock_dependencies):
        """Test execute with valid context."""
        handler = OHLCVArgumentHandler()

        context = {
            "tickers": ["AAPL", "MSFT"],
            "frequency_type": FrequencyType.DAILY,
            "frequency_value": 1,
            "period_type": PeriodType.YEAR,
            "period_value": 10,
        }

        handler.execute(context)

        # Verify logs were called
        mock_dependencies["logger_instance"].info.assert_called()

    def test_execute_with_missing_tickers(self, mock_dependencies):
        """Test execute handles missing tickers."""
        handler = OHLCVArgumentHandler()

        context = {}

        handler.execute(context)

        # Verify error was logged
        mock_dependencies["logger_instance"].error.assert_called()

    def test_execute_processes_all_tickers(self, mock_dependencies):
        """Test execute processes all tickers in context."""
        handler = OHLCVArgumentHandler()

        tickers = ["AAPL", "MSFT", "GOOGL"]
        context = {
            "tickers": tickers,
            "frequency_type": FrequencyType.DAILY,
            "frequency_value": 1,
            "period_type": PeriodType.YEAR,
            "period_value": 10,
        }

        handler.execute(context)

        # Verify processing was logged for each ticker
        assert mock_dependencies["logger_instance"].info.call_count > 0
