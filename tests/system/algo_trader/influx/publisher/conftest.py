"""Shared fixtures for influx publisher tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.

Note: Helper functions for queue_processor tests are defined in test_queue_processor.py
due to Bazel's test runner not auto-importing conftest functions the same way pytest does.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_influx_client():
    """Mock MarketDataInflux client for config tests."""
    with patch("system.algo_trader.influx.publisher.config.MarketDataInflux") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield {"class": mock_client_class, "instance": mock_client}


@pytest.fixture
def mock_dependencies_config(mock_logger, mock_influx_client):
    """Composite fixture for config tests with logger and influx client."""
    return {
        "logger": mock_logger,
        "influx_client": mock_influx_client,
    }
