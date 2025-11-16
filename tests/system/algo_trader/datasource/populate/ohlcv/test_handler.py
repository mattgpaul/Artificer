"""Unit and E2E tests for OHLCVArgumentHandler.

Tests cover initialization, argument parsing, ticker resolution, frequency/period
validation, bad ticker verification, and complete handler workflows. All external
dependencies are mocked via conftest.py. E2E tests use 'debug' database.
"""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.datasource.populate.ohlcv.handler import OHLCVArgumentHandler
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class TestOHLCVArgumentHandlerInitialization:
    """Test OHLCVArgumentHandler initialization."""

    @pytest.mark.unit
    def test_initialization(self, mock_logger):
        """Test handler initialization."""
        handler = OHLCVArgumentHandler()
        assert handler.name == "ohlcv"
        assert handler.logger is not None


class TestOHLCVArgumentHandlerAddArguments:
    """Test add_arguments method."""

    @pytest.mark.unit
    def test_add_arguments_all_options(self, ohlcv_handler):
        """Test adding all argument options."""
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
                "--verify-bad-tickers",
            ]
        )

        assert args.tickers == ["AAPL", "MSFT"]
        assert args.frequency == "daily"
        assert args.period == "year"
        assert args.frequency_value == 1
        assert args.period_value == 10
        assert args.verify_bad_tickers is True

    @pytest.mark.unit
    def test_add_arguments_defaults(self, ohlcv_handler):
        """Test argument defaults."""
        parser = argparse.ArgumentParser()
        ohlcv_handler.add_arguments(parser)

        args = parser.parse_args(["--tickers", "AAPL"])

        assert args.frequency == "daily"
        assert args.period == "year"
        assert args.frequency_value == 1
        assert args.period_value == 10
        assert args.verify_bad_tickers is False


class TestOHLCVArgumentHandlerIsApplicable:
    """Test is_applicable method."""

    @pytest.mark.unit
    def test_is_applicable_ohlcv_command(self, ohlcv_handler):
        """Test handler applies to ohlcv command."""
        args = argparse.Namespace(command="ohlcv")
        assert ohlcv_handler.is_applicable(args) is True

    @pytest.mark.unit
    def test_is_applicable_other_command(self, ohlcv_handler):
        """Test handler does not apply to other commands."""
        args = argparse.Namespace(command="fundamentals")
        assert ohlcv_handler.is_applicable(args) is False

    @pytest.mark.unit
    def test_is_applicable_no_command(self, ohlcv_handler):
        """Test handler does not apply when no command."""
        args = argparse.Namespace()
        assert ohlcv_handler.is_applicable(args) is False


class TestOHLCVArgumentHandlerProcess:
    """Test process method."""

    @pytest.mark.unit
    def test_process_specific_tickers(
        self, ohlcv_handler, mock_logger, mock_ohlcv_bad_ticker_client
    ):
        """Test processing specific tickers."""
        args = argparse.Namespace(
            tickers=["AAPL", "MSFT"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        result = ohlcv_handler.process(args)

        assert result["tickers"] == ["AAPL", "MSFT"]
        assert result["frequency_type"] == FrequencyType.DAILY
        assert result["period_type"] == PeriodType.YEAR
        assert result["frequency_value"] == 1
        assert result["period_value"] == 10
        assert result["verify_bad_tickers"] is False

    @pytest.mark.unit
    def test_process_sp500_tickers(self, ohlcv_handler, mock_tickers, mock_ohlcv_bad_ticker_client):
        """Test processing SP500 tickers."""
        mock_tickers.get_sp500_tickers.return_value = ["AAPL", "MSFT", "GOOGL"]
        args = argparse.Namespace(
            tickers=["SP500"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        with patch(
            "system.algo_trader.datasource.populate.ohlcv.handler.get_sp500_tickers"
        ) as mock_get_sp500:
            mock_get_sp500.return_value = ["AAPL", "MSFT", "GOOGL"]

            result = ohlcv_handler.process(args)

            assert len(result["tickers"]) == 3
            assert "AAPL" in result["tickers"]

    @pytest.mark.unit
    def test_process_full_registry(self, ohlcv_handler, mock_tickers, mock_ohlcv_bad_ticker_client):
        """Test processing full-registry tickers."""
        mock_tickers.get_tickers.return_value = {
            "key1": {"ticker": "AAPL"},
            "key2": {"ticker": "MSFT"},
        }
        args = argparse.Namespace(
            tickers=["full-registry"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        result = ohlcv_handler.process(args)

        assert len(result["tickers"]) == 2
        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]

    @pytest.mark.unit
    def test_process_missing_tickers(self, ohlcv_handler, mock_ohlcv_bad_ticker_client):
        """Test processing missing-tickers."""
        mock_ohlcv_bad_ticker_client.get_missing_tickers.return_value = ["TICKER1", "TICKER2"]
        args = argparse.Namespace(
            tickers=["missing-tickers"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        result = ohlcv_handler.process(args)

        assert len(result["tickers"]) == 2
        assert "TICKER1" in result["tickers"]

    @pytest.mark.unit
    def test_process_no_tickers_without_verify(self, ohlcv_handler):
        """Test processing fails without tickers and verify flag."""
        args = argparse.Namespace(
            tickers=None,
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        with pytest.raises(ValueError, match="--tickers is required"):
            ohlcv_handler.process(args)

    @pytest.mark.unit
    def test_process_no_tickers_with_verify(self, ohlcv_handler):
        """Test processing succeeds with verify flag and no tickers."""
        args = argparse.Namespace(
            tickers=None,
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=True,
        )

        result = ohlcv_handler.process(args)

        assert result["tickers"] == []
        assert result["verify_bad_tickers"] is True

    @pytest.mark.unit
    def test_process_frequency_period_validation(self, ohlcv_handler, mock_ohlcv_bad_ticker_client):
        """Test frequency and period type validation."""
        args = argparse.Namespace(
            tickers=["AAPL"],
            frequency="daily",
            period="month",
            frequency_value=1,
            period_value=6,
            verify_bad_tickers=False,
        )

        result = ohlcv_handler.process(args)

        assert result["frequency_type"] == FrequencyType.DAILY
        assert result["period_type"] == PeriodType.MONTH
        assert result["frequency_value"] == 1
        assert result["period_value"] == 6

    @pytest.mark.unit
    def test_process_verify_bad_tickers_flag(self, ohlcv_handler, mock_ohlcv_bad_ticker_client):
        """Test verify_bad_tickers flag handling."""
        args = argparse.Namespace(
            tickers=["AAPL"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=True,
        )

        result = ohlcv_handler.process(args)

        assert result["verify_bad_tickers"] is True

    @pytest.mark.unit
    def test_process_sp500_failure(self, ohlcv_handler):
        """Test handling SP500 fetch failure."""
        args = argparse.Namespace(
            tickers=["SP500"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        with patch(
            "system.algo_trader.datasource.populate.ohlcv.handler.get_sp500_tickers"
        ) as mock_get_sp500:
            mock_get_sp500.return_value = []

            with pytest.raises(ValueError, match="Failed to retrieve S&P 500 tickers"):
                ohlcv_handler.process(args)

    @pytest.mark.unit
    def test_process_full_registry_failure(self, ohlcv_handler, mock_tickers):
        """Test handling full-registry fetch failure."""
        mock_tickers.get_tickers.return_value = None
        args = argparse.Namespace(
            tickers=["full-registry"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        with pytest.raises(ValueError, match="Failed to retrieve tickers from SEC"):
            ohlcv_handler.process(args)

    @pytest.mark.unit
    def test_process_missing_tickers_empty(self, ohlcv_handler, mock_ohlcv_bad_ticker_client):
        """Test handling empty missing tickers."""
        mock_ohlcv_bad_ticker_client.get_missing_tickers.return_value = []
        args = argparse.Namespace(
            tickers=["missing-tickers"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        with pytest.raises(ValueError, match="No missing tickers found"):
            ohlcv_handler.process(args)

    @pytest.mark.e2e
    def test_process_complete_workflow(
        self, ohlcv_handler, mock_tickers, mock_ohlcv_bad_ticker_client
    ):
        """Test complete handler workflow."""
        args = argparse.Namespace(
            tickers=["AAPL", "MSFT"],
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=False,
        )

        with patch(
            "system.algo_trader.datasource.populate.ohlcv.handler.OHLCVProcessor"
        ) as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor

            result = ohlcv_handler.process(args)
            ohlcv_handler.execute(result)

            mock_processor_class.assert_called_once()
            mock_processor.process_tickers.assert_called_once()

    @pytest.mark.e2e
    def test_process_verify_bad_tickers_workflow(self, ohlcv_handler, mock_ohlcv_bad_ticker_client):
        """Test verify bad tickers workflow."""
        args = argparse.Namespace(
            tickers=None,
            frequency="daily",
            period="year",
            frequency_value=1,
            period_value=10,
            verify_bad_tickers=True,
        )

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.handler.BadTickerVerifier"
            ) as mock_verifier_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.handler.OHLCVProcessor"
            ) as mock_processor_class,
        ):
            mock_verifier = MagicMock()
            mock_verifier_class.return_value = mock_verifier
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor

            result = ohlcv_handler.process(args)
            ohlcv_handler.execute(result)

            mock_verifier_class.assert_called_once()
            mock_verifier.verify_bad_tickers.assert_called_once()
