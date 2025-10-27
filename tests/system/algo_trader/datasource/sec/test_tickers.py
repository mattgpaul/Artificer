"""Unit tests for Tickers - SEC Ticker Data Retrieval.

Tests cover successful data retrieval, error handling, rate limiting, and
network failure scenarios. All external dependencies are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.datasource.sec.tickers import Tickers


class TestTickersInitialization:
    """Test Tickers initialization."""

    @pytest.fixture
    def tickers(self):
        """Fixture to create a Tickers instance with mocked logger."""
        with patch("system.algo_trader.datasource.sec.tickers.get_logger") as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            yield Tickers()

    def test_initialization_success(self, tickers):
        """Test Tickers initializes correctly."""
        assert tickers is not None
        assert hasattr(tickers, "logger")


class TestGetTickersSuccess:
    """Test successful ticker data retrieval."""

    @pytest.fixture
    def tickers(self):
        """Fixture to create a Tickers instance with mocked logger."""
        with patch("system.algo_trader.datasource.sec.tickers.get_logger") as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            yield Tickers()

    def test_get_tickers_success(self, tickers):
        """Test successful retrieval of ticker data from SEC."""
        mock_response_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
        }

        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result == mock_response_data
            # Verify correct headers were sent
            call_args = mock_get.call_args
            assert "headers" in call_args.kwargs
            assert call_args.kwargs["headers"]["User-Agent"] == "Company Name company@email.com"
            assert call_args.kwargs["headers"]["Accept"] == "application/json"

    def test_get_tickers_returns_none_on_exception(self, tickers):
        """Test get_tickers returns None when an exception occurs."""
        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()


class TestGetTickersErrorHandling:
    """Test error handling for various failure scenarios."""

    @pytest.fixture
    def tickers(self):
        """Fixture to create a Tickers instance with mocked logger."""
        with patch("system.algo_trader.datasource.sec.tickers.get_logger") as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            yield Tickers()

    def test_get_tickers_non_200_status_code(self, tickers):
        """Test get_tickers handles non-200 HTTP status codes."""
        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()
            # Verify response preview was logged
            tickers.logger.info.assert_called()
            log_call = str(tickers.logger.info.call_args)
            assert "Not Found" in log_call

    def test_get_tickers_html_response_instead_of_json(self, tickers):
        """Test get_tickers handles HTML response (e.g., rate limiting page)."""
        html_content = "<html><body>Rate Limit Exceeded</body></html>"

        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.text = html_content
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()
            # Verify response preview was logged
            tickers.logger.info.assert_called()
            log_call = str(tickers.logger.info.call_args)
            assert html_content in log_call

    def test_get_tickers_no_content_type(self, tickers):
        """Test get_tickers handles missing Content-Type header."""
        mock_response_data = {"test": "data"}

        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}  # No Content-Type header
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()

    def test_get_tickers_json_decode_error(self, tickers):
        """Test get_tickers handles JSON decode errors."""
        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()


class TestGetTickersRateLimiting:
    """Test handling of SEC rate limiting scenarios."""

    @pytest.fixture
    def tickers(self):
        """Fixture to create a Tickers instance with mocked logger."""
        with patch("system.algo_trader.datasource.sec.tickers.get_logger") as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            yield Tickers()

    def test_get_tickers_sec_rate_limit_response(self, tickers):
        """Test get_tickers handles SEC rate limiting HTML page."""
        rate_limit_html = (
            "<!DOCTYPE html>"
            "<html><head><title>Request Rate Threshold Exceeded</title></head>"
            "<body><h1>Automated access to our sites...</h1></body></html>"
        )

        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.text = rate_limit_html
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()
            # Verify the rate limit content was logged
            log_call = str(tickers.logger.info.call_args)
            assert "Request Rate Threshold Exceeded" in log_call or "rate_limit_html" in log_call

    def test_get_tickers_with_proper_headers(self, tickers):
        """Test that proper headers are sent to SEC API."""
        mock_response_data = {"test": "data"}

        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            tickers.get_tickers()

            # Verify the request was made with correct headers
            call_args = mock_get.call_args
            assert "headers" in call_args.kwargs
            headers = call_args.kwargs["headers"]
            assert "User-Agent" in headers
            assert "Accept" in headers
            assert "Accept-Encoding" in headers


class TestGetTickersResponseValidation:
    """Test response validation and content type checks."""

    @pytest.fixture
    def tickers(self):
        """Fixture to create a Tickers instance with mocked logger."""
        with patch("system.algo_trader.datasource.sec.tickers.get_logger") as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            yield Tickers()

    def test_content_type_variations(self, tickers):
        """Test that various JSON content type formats are accepted."""
        valid_content_types = [
            "application/json",
            "application/json; charset=utf-8",
            "text/json",
            "application/vnd.api+json",
        ]

        for content_type in valid_content_types:
            with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.headers = {"Content-Type": content_type}
                mock_response.json.return_value = {"data": "test"}
                mock_get.return_value = mock_response

                result = tickers.get_tickers()

                assert result is not None

    def test_invalid_content_types_rejected(self, tickers):
        """Test that non-JSON content types are rejected."""
        invalid_content_types = [
            "text/html",
            "text/plain",
            "application/xml",
            "image/png",
            "",
        ]

        for content_type in invalid_content_types:
            with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.headers = {"Content-Type": content_type}
                mock_get.return_value = mock_response

                result = tickers.get_tickers()

                assert result is None


class TestGetTickersEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def tickers(self):
        """Fixture to create a Tickers instance with mocked logger."""
        with patch("system.algo_trader.datasource.sec.tickers.get_logger") as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            yield Tickers()

    def test_empty_response(self, tickers):
        """Test handling of empty response."""
        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.return_value = {}
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result == {}

    def test_large_response_preview_logged(self, tickers):
        """Test that only first 500 characters of error response are logged."""
        large_response = "x" * 1000

        with patch("system.algo_trader.datasource.sec.tickers.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = large_response
            mock_get.return_value = mock_response

            tickers.get_tickers()

            # Verify only 500 chars were logged
            tickers.logger.info.assert_called()
            logged_text = str(tickers.logger.info.call_args)
            # The preview should be limited
            assert len(logged_text) < 1000
