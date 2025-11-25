"""Unit tests for BadTickerVerifier.

Tests cover verification of bad tickers and removal from bad_tickers list.
The verifier returns recovered tickers which are then processed by OHLCVProcessor.
"""

from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.datasource.populate.ohlcv.verifier import BadTickerVerifier
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class TestBadTickerVerifierInitialization:
    """Test BadTickerVerifier initialization."""

    @pytest.mark.unit
    def test_initialization_default_logger(self):
        """Test initialization creates default logger."""
        with patch(
            "system.algo_trader.datasource.populate.ohlcv.verifier.get_logger"
        ) as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            verifier = BadTickerVerifier()

            assert verifier.logger == mock_logger
            mock_get_logger.assert_called_once_with("BadTickerVerifier")

    @pytest.mark.unit
    def test_initialization_custom_logger(self):
        """Test initialization with custom logger."""
        custom_logger = MagicMock()
        verifier = BadTickerVerifier(logger=custom_logger)

        assert verifier.logger == custom_logger


class TestBadTickerVerifierVerifyBadTickers:
    """Test verify_bad_tickers method."""

    @pytest.mark.unit
    def test_verify_bad_tickers_no_bad_tickers(self, mock_logger):
        """Test verify_bad_tickers with no bad tickers returns empty list."""
        with patch(
            "system.algo_trader.datasource.populate.ohlcv.verifier.BadTickerClient"
        ) as mock_bad_ticker_client_class:
            mock_bad_ticker_client = MagicMock()
            mock_bad_ticker_client.get_bad_tickers.return_value = []
            mock_bad_ticker_client_class.return_value = mock_bad_ticker_client

            verifier = BadTickerVerifier(logger=mock_logger)
            result = verifier.verify_bad_tickers(
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.YEAR,
                period_value=10,
            )

            assert result == []
            mock_bad_ticker_client.get_bad_tickers.assert_called_once_with(limit=10000)
            mock_logger.info.assert_any_call("No bad tickers found in MySQL")

    @pytest.mark.unit
    def test_verify_bad_tickers_valid_data_removes_and_returns(self, mock_logger):
        """Test verify_bad_tickers removes ticker and returns it when valid."""
        mock_response = {
            "candles": [
                {"datetime": 1000, "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000000},
                {"datetime": 2000, "open": 104.0, "high": 106.0, "low": 103.0, "close": 105.0, "volume": 1100000},
            ]
        }

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.BadTickerClient"
            ) as mock_bad_ticker_client_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.MarketHandler"
            ) as mock_market_handler_class,
        ):
            mock_bad_ticker_client = MagicMock()
            mock_bad_ticker_client.get_bad_tickers.return_value = [
                {"ticker": "AAPL", "timestamp": "2024-01-01T00:00:00", "reason": "No data"}
            ]
            mock_bad_ticker_client.remove_bad_ticker.return_value = True
            mock_bad_ticker_client_class.return_value = mock_bad_ticker_client

            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = mock_response
            mock_market_handler_class.return_value = mock_market_handler

            verifier = BadTickerVerifier(logger=mock_logger)
            result = verifier.verify_bad_tickers(
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.YEAR,
                period_value=10,
            )

            # Verify market handler was called
            mock_market_handler.get_price_history.assert_called_once_with(
                ticker="AAPL",
                period_type=PeriodType.YEAR,
                period=10,
                frequency_type=FrequencyType.DAILY,
                frequency=1,
            )

            # Verify ticker was removed from bad_tickers
            mock_bad_ticker_client.remove_bad_ticker.assert_called_once_with("AAPL")

            # Verify ticker is returned in result
            assert result == ["AAPL"]

            # Verify logging
            mock_logger.info.assert_any_call(
                "Removed AAPL from bad_tickers (now has valid data)"
            )
            mock_logger.info.assert_any_call(
                f"Found 1 recovered tickers to process: ['AAPL']"
            )

    @pytest.mark.unit
    def test_verify_bad_tickers_still_bad_no_remove(self, mock_logger):
        """Test verify_bad_tickers does not remove when ticker is still bad."""
        mock_response = {"candles": []}  # Empty candles means still bad

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.BadTickerClient"
            ) as mock_bad_ticker_client_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.MarketHandler"
            ) as mock_market_handler_class,
        ):
            mock_bad_ticker_client = MagicMock()
            mock_bad_ticker_client.get_bad_tickers.return_value = [
                {"ticker": "BAD", "timestamp": "2024-01-01T00:00:00", "reason": "No data"}
            ]
            mock_bad_ticker_client_class.return_value = mock_bad_ticker_client

            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = mock_response
            mock_market_handler_class.return_value = mock_market_handler

            verifier = BadTickerVerifier(logger=mock_logger)
            result = verifier.verify_bad_tickers(
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.YEAR,
                period_value=10,
            )

            # Verify ticker was NOT removed
            mock_bad_ticker_client.remove_bad_ticker.assert_not_called()

            # Verify empty result
            assert result == []

            # Verify debug log
            mock_logger.debug.assert_any_call("BAD is still bad")

    @pytest.mark.unit
    def test_verify_bad_tickers_remove_failure_does_not_return(self, mock_logger):
        """Test that if remove fails, ticker is not returned."""
        mock_response = {
            "candles": [
                {"datetime": 1000, "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000000},
            ]
        }

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.BadTickerClient"
            ) as mock_bad_ticker_client_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.MarketHandler"
            ) as mock_market_handler_class,
        ):
            mock_bad_ticker_client = MagicMock()
            mock_bad_ticker_client.get_bad_tickers.return_value = [
                {"ticker": "AAPL", "timestamp": "2024-01-01T00:00:00", "reason": "No data"}
            ]
            mock_bad_ticker_client.remove_bad_ticker.return_value = False  # Remove fails
            mock_bad_ticker_client_class.return_value = mock_bad_ticker_client

            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = mock_response
            mock_market_handler_class.return_value = mock_market_handler

            verifier = BadTickerVerifier(logger=mock_logger)
            result = verifier.verify_bad_tickers(
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.YEAR,
                period_value=10,
            )

            # Verify remove was attempted
            mock_bad_ticker_client.remove_bad_ticker.assert_called_once_with("AAPL")

            # Verify ticker was NOT returned (because remove failed)
            assert result == []

            # Verify error logging
            mock_logger.error.assert_any_call("Failed to remove AAPL from bad_tickers")

    @pytest.mark.unit
    def test_verify_bad_tickers_multiple_tickers(self, mock_logger):
        """Test verify_bad_tickers with multiple tickers."""
        mock_response_valid = {
            "candles": [
                {"datetime": 1000, "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000000},
            ]
        }
        mock_response_invalid = {"candles": []}

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.BadTickerClient"
            ) as mock_bad_ticker_client_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.MarketHandler"
            ) as mock_market_handler_class,
        ):
            mock_bad_ticker_client = MagicMock()
            mock_bad_ticker_client.get_bad_tickers.return_value = [
                {"ticker": "AAPL", "timestamp": "2024-01-01T00:00:00", "reason": "No data"},
                {"ticker": "BAD", "timestamp": "2024-01-01T00:00:00", "reason": "No data"},
                {"ticker": "MSFT", "timestamp": "2024-01-01T00:00:00", "reason": "No data"},
            ]
            mock_bad_ticker_client.remove_bad_ticker.return_value = True
            mock_bad_ticker_client_class.return_value = mock_bad_ticker_client

            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.side_effect = [
                mock_response_valid,  # AAPL - valid
                mock_response_invalid,  # BAD - still bad
                mock_response_valid,  # MSFT - valid
            ]
            mock_market_handler_class.return_value = mock_market_handler

            verifier = BadTickerVerifier(logger=mock_logger)
            result = verifier.verify_bad_tickers(
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.YEAR,
                period_value=10,
            )

            # Verify remove_bad_ticker was called twice (for AAPL and MSFT)
            assert mock_bad_ticker_client.remove_bad_ticker.call_count == 2
            mock_bad_ticker_client.remove_bad_ticker.assert_any_call("AAPL")
            mock_bad_ticker_client.remove_bad_ticker.assert_any_call("MSFT")
            mock_bad_ticker_client.remove_bad_ticker.assert_not_called_with("BAD")

            # Verify result contains recovered tickers
            assert set(result) == {"AAPL", "MSFT"}
            assert len(result) == 2

            # Verify summary logging
            summary_log_calls = [
                call for call in mock_logger.info.call_args_list if "Verification complete" in str(call)
            ]
            assert len(summary_log_calls) == 1
            assert "2 removed" in str(summary_log_calls[0])

    @pytest.mark.unit
    def test_verify_bad_tickers_handles_exception(self, mock_logger):
        """Test verify_bad_tickers handles exceptions during verification."""
        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.BadTickerClient"
            ) as mock_bad_ticker_client_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.verifier.MarketHandler"
            ) as mock_market_handler_class,
        ):
            mock_bad_ticker_client = MagicMock()
            mock_bad_ticker_client.get_bad_tickers.return_value = [
                {"ticker": "AAPL", "timestamp": "2024-01-01T00:00:00", "reason": "No data"}
            ]
            mock_bad_ticker_client_class.return_value = mock_bad_ticker_client

            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.side_effect = Exception("API error")
            mock_market_handler_class.return_value = mock_market_handler

            verifier = BadTickerVerifier(logger=mock_logger)
            result = verifier.verify_bad_tickers(
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.YEAR,
                period_value=10,
            )

            # Verify error was logged
            mock_logger.error.assert_any_call("Error verifying ticker AAPL: API error")

            # Verify no removal happened and empty result
            mock_bad_ticker_client.remove_bad_ticker.assert_not_called()
            assert result == []

