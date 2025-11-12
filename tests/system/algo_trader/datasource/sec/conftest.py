"""Shared fixtures for SEC datasource tests."""

from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.datasource.sec.tickers import Tickers


@pytest.fixture(autouse=True)
def auto_mock_external_calls():
    """Automatically mock external calls to prevent hangs."""
    with patch("system.algo_trader.datasource.sec.tickers.requests.get"):
        yield


@pytest.fixture
def mock_logger():
    """Fixture to mock logger for Tickers."""
    with patch("system.algo_trader.datasource.sec.tickers.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def tickers(mock_logger):
    """Fixture to create a Tickers instance with mocked logger."""
    return Tickers()


@pytest.fixture
def tickers_with_mocked_time(mock_logger):
    """Fixture to create a Tickers instance with mocked logger and time."""
    with patch("system.algo_trader.datasource.sec.tickers.time") as mock_time:
        mock_time.time.return_value = 1000000.0
        yield Tickers()


@pytest.fixture
def mock_http_response():
    """Fixture factory to create mock HTTP responses."""

    def _create_response(status_code=200, content_type="application/json", text="", json_data=None):
        """Create a mock HTTP response with specified attributes."""
        response = MagicMock()
        response.status_code = status_code
        response.headers = {"Content-Type": content_type}
        response.text = text
        if json_data is not None:
            response.json.return_value = json_data
        return response

    return _create_response
