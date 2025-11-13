"""Unit tests for OHLCVArgumentHandler - OHLCV data population handler.

Tests cover initialization, argument parsing, ticker fetching, validation,
and execution logic. All external dependencies are mocked via conftest.py.
"""

import argparse
from unittest.mock import Mock, patch

import pytest

from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class TestOHLCVArgumentHandler:
    """Test OHLCV handler core functionality."""

    def test_initialization(self, ohlcv_handler):
        """Test handler initializes correctly."""
        assert ohlcv_handler.name == "ohlcv"
        assert ohlcv_handler.logger is not None

    def test_is_applicable(self, ohlcv_handler):
        """Test is_applicable method."""
        assert ohlcv_handler.is_applicable(argparse.Namespace(command="ohlcv")) is True
        assert ohlcv_handler.is_applicable(argparse.Namespace(command="other")) is False

    def test_add_arguments(self, ohlcv_handler):
        """Test all arguments are added correctly."""
        parser = argparse.ArgumentParser()
        ohlcv_handler.add_arguments(parser)

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
        assert args.frequency == "daily"
        assert args.period == "year"
        assert args.frequency_value == 1
        assert args.period_value == 10

    @pytest.mark.parametrize(
        "tickers,verify_flag,should_raise",
        [
            (["AAPL"], False, False),
            (None, True, False),
            (None, False, True),
        ],
    )
    def test_process_ticker_validation(
        self,
        ohlcv_handler,
        mock_tickers,
        mock_ohlcv_bad_ticker_client,
        tickers,
        verify_flag,
        should_raise,
    ):
        """Test process validates tickers or verify flag."""
        parser = argparse.ArgumentParser()
        ohlcv_handler.add_arguments(parser)
        args = parser.parse_args(
            [
                *(["--tickers", *tickers] if tickers else []),
                *(["--verify-bad-tickers"] if verify_flag else []),
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

        if should_raise:
            with pytest.raises(ValueError, match="--tickers is required"):
                ohlcv_handler.process(args)
        else:
            result = ohlcv_handler.process(args)
            assert "tickers" in result
            assert "frequency_type" in result
            assert "period_type" in result

    def test_process_with_full_registry(
        self, ohlcv_handler, mock_tickers, mock_ohlcv_bad_ticker_client
    ):
        """Test process with full-registry fetches all tickers."""
        mock_tickers.get_tickers.return_value = {
            "0": {"ticker": "AAPL", "cik_str": 123},
            "1": {"ticker": "MSFT", "cik_str": 456},
        }

        parser = argparse.ArgumentParser()
        ohlcv_handler.add_arguments(parser)
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

        result = ohlcv_handler.process(args)
        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]
        mock_tickers.get_tickers.assert_called_once()

    def test_process_filters_bad_tickers(
        self, ohlcv_handler, mock_tickers, mock_ohlcv_bad_ticker_client
    ):
        """Test process filters out bad tickers."""
        mock_ohlcv_bad_ticker_client.is_bad_ticker.side_effect = lambda t: t == "MSFT"

        parser = argparse.ArgumentParser()
        ohlcv_handler.add_arguments(parser)
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

        result = ohlcv_handler.process(args)
        assert "AAPL" in result["tickers"]
        assert "MSFT" not in result["tickers"]
        assert "GOOGL" in result["tickers"]

    @pytest.mark.parametrize(
        "frequency,period,freq_value,period_value,should_raise",
        [
            ("daily", "year", 1, 10, False),
            ("minute", "year", 1, 1, True),  # Invalid combination
            ("daily", "year", 5, 10, True),  # Invalid frequency value
        ],
    )
    def test_process_validates_frequency_period(
        self,
        ohlcv_handler,
        mock_ohlcv_bad_ticker_client,
        frequency,
        period,
        freq_value,
        period_value,
        should_raise,
    ):
        """Test process validates frequency and period combinations."""
        parser = argparse.ArgumentParser()
        ohlcv_handler.add_arguments(parser)
        args = parser.parse_args(
            [
                "--tickers",
                "AAPL",
                "--frequency",
                frequency,
                "--period",
                period,
                "--frequency-value",
                str(freq_value),
                "--period-value",
                str(period_value),
            ]
        )

        if should_raise:
            with pytest.raises(ValueError):
                ohlcv_handler.process(args)
        else:
            result = ohlcv_handler.process(args)
            assert result["frequency_type"] == FrequencyType(frequency)
            assert result["period_type"] == PeriodType(period)

    def test_process_handles_sec_fetch_failure(
        self, ohlcv_handler, mock_tickers, mock_ohlcv_bad_ticker_client
    ):
        """Test process handles SEC fetch failure."""
        mock_tickers.get_tickers.return_value = None

        parser = argparse.ArgumentParser()
        ohlcv_handler.add_arguments(parser)
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
            ohlcv_handler.process(args)

    def test_execute_with_verify_bad_tickers(self, ohlcv_handler, mock_ohlcv_bad_ticker_client):
        """Test execute calls verify_bad_tickers when flag is set."""
        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.handler.BadTickerVerifier"
            ) as mock_verifier_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.handler.OHLCVProcessor"
            ) as mock_processor_class,
        ):
            mock_verifier = Mock()
            mock_verifier_class.return_value = mock_verifier
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor

            context = {
                "tickers": [],
                "frequency_type": FrequencyType.DAILY,
                "frequency_value": 1,
                "period_type": PeriodType.YEAR,
                "period_value": 10,
                "verify_bad_tickers": True,
            }

            ohlcv_handler.execute(context)
            mock_verifier.verify_bad_tickers.assert_called_once()

    def test_execute_with_tickers(self, ohlcv_handler):
        """Test execute processes tickers."""
        with patch(
            "system.algo_trader.datasource.populate.ohlcv.handler.OHLCVProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor

            context = {
                "tickers": ["AAPL", "MSFT"],
                "frequency_type": FrequencyType.DAILY,
                "frequency_value": 1,
                "period_type": PeriodType.YEAR,
                "period_value": 10,
            }

            ohlcv_handler.execute(context)
            mock_processor.process_tickers.assert_called_once()

    def test_execute_handles_missing_tickers(self, ohlcv_handler):
        """Test execute handles missing tickers gracefully."""
        context = {}
        ohlcv_handler.execute(context)
        ohlcv_handler.logger.error.assert_called()
