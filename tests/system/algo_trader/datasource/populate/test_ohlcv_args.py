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
        patch(
            "system.algo_trader.datasource.populate.ohlcv_args.BadTickerClient"
        ) as mock_bad_ticker_client,
    ):
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance

        # Mock BadTickerClient instance
        mock_bad_ticker_instance = Mock()
        mock_bad_ticker_instance.is_bad_ticker.return_value = False
        mock_bad_ticker_instance.get_bad_tickers.return_value = []
        mock_bad_ticker_instance.remove_bad_ticker.return_value = True
        mock_bad_ticker_client.return_value = mock_bad_ticker_instance

        yield {
            "logger": mock_logger,
            "logger_instance": mock_logger_instance,
            "tickers": mock_tickers,
            "bad_ticker_client": mock_bad_ticker_client,
            "bad_ticker_instance": mock_bad_ticker_instance,
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

    def test_adds_verify_bad_tickers_argument(self, mock_dependencies, parser):
        """Test verify-bad-tickers argument is added."""
        handler = OHLCVArgumentHandler()
        handler.add_arguments(parser)

        args = parser.parse_args(
            [
                "--verify-bad-tickers",
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

        assert args.verify_bad_tickers is True

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
        assert result["verify_bad_tickers"] is False

    def test_process_filters_bad_tickers(self, mock_dependencies):
        """Test process filters out bad tickers from MySQL."""
        handler = OHLCVArgumentHandler()

        # Mock BadTickerClient to mark MSFT as bad
        mock_dependencies["bad_ticker_instance"].is_bad_ticker.side_effect = (
            lambda ticker: ticker == "MSFT"
        )

        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)
        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "MSFT",
                "GOOGL",
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

        # MSFT should be filtered out
        assert "AAPL" in result["tickers"]
        assert "MSFT" not in result["tickers"]
        assert "GOOGL" in result["tickers"]
        assert len(result["tickers"]) == 2
        mock_dependencies["bad_ticker_instance"].is_bad_ticker.assert_called()

    def test_process_with_verify_bad_tickers_flag(self, mock_dependencies):
        """Test process with --verify-bad-tickers flag."""
        handler = OHLCVArgumentHandler()

        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)
        args = parser.parse_args(
            [
                "--verify-bad-tickers",
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

        assert result["verify_bad_tickers"] is True
        assert result["tickers"] == []

    def test_process_requires_tickers_or_verify_flag(self, mock_dependencies):
        """Test process requires either tickers or verify-bad-tickers flag."""
        handler = OHLCVArgumentHandler()

        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)
        args = parser.parse_args(
            [
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

        with pytest.raises(
            ValueError, match="--tickers is required unless --verify-bad-tickers is used"
        ):
            handler.process(args)

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

    def test_process_with_full_registry_filters_bad_tickers(self, mock_dependencies):
        """Test process filters bad tickers when using full-registry."""
        handler = OHLCVArgumentHandler()

        # Mock ticker data
        mock_ticker_source = Mock()
        mock_ticker_source.get_tickers.return_value = {
            "0": {"ticker": "AAPL", "cik_str": 123},
            "1": {"ticker": "MSFT", "cik_str": 456},
            "2": {"ticker": "GOOGL", "cik_str": 789},
        }
        mock_dependencies["tickers"].return_value = mock_ticker_source

        # Mock BadTickerClient to mark MSFT as bad
        mock_dependencies["bad_ticker_instance"].is_bad_ticker.side_effect = (
            lambda ticker: ticker == "MSFT"
        )

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

        # MSFT should be filtered out
        assert "AAPL" in result["tickers"]
        assert "MSFT" not in result["tickers"]
        assert "GOOGL" in result["tickers"]
        assert len(result["tickers"]) == 2


class TestOHLCVArgumentHandlerVerifyBadTickers:
    """Test verify_bad_tickers functionality."""

    def test_verify_bad_tickers_with_no_bad_tickers(self, mock_dependencies):
        """Test verify_bad_tickers when no bad tickers exist."""
        handler = OHLCVArgumentHandler()

        with patch("system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"):
            mock_dependencies["bad_ticker_instance"].get_bad_tickers.return_value = []

            handler._verify_bad_tickers(FrequencyType.DAILY, 1, PeriodType.YEAR, 10)

            mock_dependencies["logger_instance"].info.assert_called()
            mock_dependencies["bad_ticker_instance"].get_bad_tickers.assert_called_once_with(
                limit=10000
            )

    def test_verify_bad_tickers_removes_good_tickers(self, mock_dependencies):
        """Test verify_bad_tickers removes tickers that are no longer bad."""
        handler = OHLCVArgumentHandler()

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"
            ) as mock_market_handler_class,
        ):
            # Mock bad tickers
            mock_dependencies["bad_ticker_instance"].get_bad_tickers.return_value = [
                {"ticker": "AAPL", "timestamp": "2024-01-01", "reason": "Empty response"},
                {"ticker": "MSFT", "timestamp": "2024-01-01", "reason": "No candles data"},
            ]

            # Mock MarketHandler - AAPL now has valid data, MSFT still bad
            mock_market_handler = Mock()
            mock_market_handler.get_price_history.side_effect = [
                {
                    "candles": [
                        {
                            "datetime": 1234567890,
                            "open": 150.0,
                            "high": 155.0,
                            "low": 149.0,
                            "close": 154.0,
                            "volume": 1000000,
                        }
                    ]
                },  # AAPL - valid
                {},  # MSFT - still bad
            ]
            mock_market_handler_class.return_value = mock_market_handler

            handler._verify_bad_tickers(FrequencyType.DAILY, 1, PeriodType.YEAR, 10)

            # AAPL should be removed (has valid data)
            mock_dependencies["bad_ticker_instance"].remove_bad_ticker.assert_called_with("AAPL")
            # MSFT should not be removed (still bad)
            assert mock_dependencies["bad_ticker_instance"].remove_bad_ticker.call_count == 1

    def test_verify_bad_tickers_handles_exceptions(self, mock_dependencies):
        """Test verify_bad_tickers handles exceptions gracefully."""
        handler = OHLCVArgumentHandler()

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"
            ) as mock_market_handler_class,
        ):
            # Mock bad tickers
            mock_dependencies["bad_ticker_instance"].get_bad_tickers.return_value = [
                {"ticker": "AAPL", "timestamp": "2024-01-01", "reason": "Error"},
            ]

            # Mock MarketHandler to raise exception
            mock_market_handler = Mock()
            mock_market_handler.get_price_history.side_effect = Exception("API Error")
            mock_market_handler_class.return_value = mock_market_handler

            handler._verify_bad_tickers(FrequencyType.DAILY, 1, PeriodType.YEAR, 10)

            # Should log error but continue
            mock_dependencies["logger_instance"].error.assert_called()


class TestOHLCVArgumentHandlerExecute:
    """Test execute method with multi-threading."""

    def test_execute_with_missing_tickers(self, mock_dependencies):
        """Test execute handles missing tickers."""
        handler = OHLCVArgumentHandler()

        context = {}

        handler.execute(context)

        # Verify error was logged
        mock_dependencies["logger_instance"].error.assert_called()

    def test_execute_with_valid_context_successful(self, mock_dependencies):
        """Test execute with valid context and successful API responses."""
        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.ThreadManager"
            ) as mock_thread_manager_class,
            patch("builtins.print"),
        ):
            # Mock MarketHandler
            mock_market_handler = Mock()
            mock_market_handler.get_price_history.return_value = {
                "symbol": "AAPL",
                "candles": [
                    {
                        "datetime": 1234567890,
                        "open": 150.0,
                        "high": 155.0,
                        "low": 149.0,
                        "close": 154.0,
                        "volume": 1000000,
                    },
                    {
                        "datetime": 1234567900,
                        "open": 154.0,
                        "high": 156.0,
                        "low": 153.0,
                        "close": 155.5,
                        "volume": 1100000,
                    },
                ],
            }
            mock_market_handler_class.return_value = mock_market_handler

            # Mock ThreadManager
            mock_thread_manager = Mock()
            mock_thread_manager.config.max_threads = 10
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.cleanup_dead_threads.return_value = 2
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 2,
                "failed": 0,
                "running": 0,
                "total": 2,
            }
            mock_thread_manager_class.return_value = mock_thread_manager

            handler = OHLCVArgumentHandler()

            context = {
                "tickers": ["AAPL", "MSFT"],
                "frequency_type": FrequencyType.DAILY,
                "frequency_value": 1,
                "period_type": PeriodType.YEAR,
                "period_value": 10,
            }

            handler.execute(context)

            # Verify MarketHandler and ThreadManager were initialized
            mock_market_handler_class.assert_called_once()
            mock_thread_manager_class.assert_called_once()

            # Verify threads were started for each ticker
            assert mock_thread_manager.start_thread.call_count == 2

            # Verify wait and cleanup were called
            mock_thread_manager.wait_for_all_threads.assert_called_once()
            mock_thread_manager.cleanup_dead_threads.assert_called()
            mock_thread_manager.get_results_summary.assert_called_once()

    def test_execute_with_api_failures(self, mock_dependencies):
        """Test execute handles API failures gracefully."""
        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.ThreadManager"
            ) as mock_thread_manager_class,
            patch("builtins.print"),
        ):
            # Mock MarketHandler returning empty response
            mock_market_handler = Mock()
            mock_market_handler.get_price_history.return_value = {}
            mock_market_handler_class.return_value = mock_market_handler

            # Mock ThreadManager
            mock_thread_manager = Mock()
            mock_thread_manager.config.max_threads = 10
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.cleanup_dead_threads.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 1,
                "running": 0,
                "total": 1,
            }
            mock_thread_manager_class.return_value = mock_thread_manager

            handler = OHLCVArgumentHandler()

            context = {
                "tickers": ["INVALID"],
                "frequency_type": FrequencyType.DAILY,
                "frequency_value": 1,
                "period_type": PeriodType.YEAR,
                "period_value": 10,
            }

            handler.execute(context)

            # Verify thread was started despite failure
            assert mock_thread_manager.start_thread.call_count == 1

    def test_execute_with_empty_candles(self, mock_dependencies):
        """Test execute handles empty candles list."""
        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.ThreadManager"
            ) as mock_thread_manager_class,
            patch("builtins.print"),
        ):
            # Mock MarketHandler returning response with empty candles
            mock_market_handler = Mock()
            mock_market_handler.get_price_history.return_value = {"symbol": "AAPL", "candles": []}
            mock_market_handler_class.return_value = mock_market_handler

            # Mock ThreadManager
            mock_thread_manager = Mock()
            mock_thread_manager.config.max_threads = 10
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.cleanup_dead_threads.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 1,
                "running": 0,
                "total": 1,
            }
            mock_thread_manager_class.return_value = mock_thread_manager

            handler = OHLCVArgumentHandler()

            context = {
                "tickers": ["AAPL"],
                "frequency_type": FrequencyType.DAILY,
                "frequency_value": 1,
                "period_type": PeriodType.YEAR,
                "period_value": 10,
            }

            handler.execute(context)

            # Verify thread was started
            assert mock_thread_manager.start_thread.call_count == 1

    def test_execute_logs_batching_warning(self, mock_dependencies):
        """Test execute logs warning when batching is needed."""
        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.ThreadManager"
            ) as mock_thread_manager_class,
            patch("builtins.print"),
        ):
            # Mock MarketHandler
            mock_market_handler = Mock()
            mock_market_handler_class.return_value = mock_market_handler

            # Mock ThreadManager with low max_threads
            mock_thread_manager = Mock()
            mock_thread_manager.config.max_threads = 2
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.cleanup_dead_threads.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 5,
                "failed": 0,
                "running": 0,
                "total": 5,
            }
            mock_thread_manager_class.return_value = mock_thread_manager

            handler = OHLCVArgumentHandler()

            context = {
                "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
                "frequency_type": FrequencyType.DAILY,
                "frequency_value": 1,
                "period_type": PeriodType.YEAR,
                "period_value": 10,
            }

            handler.execute(context)

            # Verify batching warning was logged
            log_calls = [
                str(call) for call in mock_dependencies["logger_instance"].info.call_args_list
            ]
            assert any("Batching will be used" in str(call) for call in log_calls)

    def test_execute_with_verify_bad_tickers_flag(self, mock_dependencies):
        """Test execute calls verify_bad_tickers when flag is set."""
        handler = OHLCVArgumentHandler()

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.ThreadManager"
            ) as mock_thread_manager_class,
            patch("builtins.print"),
        ):
            # Mock MarketHandler for verify_bad_tickers
            mock_market_handler = Mock()
            mock_market_handler.get_price_history.return_value = {"candles": []}
            mock_market_handler_class.return_value = mock_market_handler

            # Mock ThreadManager
            mock_thread_manager = Mock()
            mock_thread_manager.config.max_threads = 4
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
                "running": 0,
                "total": 0,
            }
            mock_thread_manager_class.return_value = mock_thread_manager

            # Mock bad tickers for verification
            mock_dependencies["bad_ticker_instance"].get_bad_tickers.return_value = []

            context = {
                "tickers": [],
                "frequency_type": FrequencyType.DAILY,
                "frequency_value": 1,
                "period_type": PeriodType.YEAR,
                "period_value": 10,
                "verify_bad_tickers": True,
            }

            handler.execute(context)

            # Verify verify_bad_tickers was called
            mock_dependencies["bad_ticker_instance"].get_bad_tickers.assert_called_once_with(
                limit=10000
            )

    def test_execute_with_verify_bad_tickers_and_no_tickers(self, mock_dependencies):
        """Test execute with verify_bad_tickers flag and no tickers."""
        handler = OHLCVArgumentHandler()

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv_args.MarketHandler"
            ) as mock_market_handler_class,
            patch("builtins.print"),
        ):
            # Mock MarketHandler for verify_bad_tickers
            mock_market_handler = Mock()
            mock_market_handler.get_price_history.return_value = {"candles": []}
            mock_market_handler_class.return_value = mock_market_handler

            # Mock bad tickers for verification
            mock_dependencies["bad_ticker_instance"].get_bad_tickers.return_value = []

            context = {
                "tickers": None,
                "frequency_type": FrequencyType.DAILY,
                "frequency_value": 1,
                "period_type": PeriodType.YEAR,
                "period_value": 10,
                "verify_bad_tickers": True,
            }

            handler.execute(context)

            # Should not error when tickers is None but verify_bad_tickers is True
            mock_dependencies["logger_instance"].error.assert_not_called()
