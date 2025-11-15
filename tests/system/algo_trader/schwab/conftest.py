"""Shared fixtures for Schwab client tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Auto-mock required Schwab environment variables."""
    with patch.dict(
        os.environ,
        {
            "SCHWAB_API_KEY": "test_api_key",
            "SCHWAB_SECRET": "test_secret",
            "SCHWAB_APP_NAME": "test_app_name",
        },
    ):
        yield


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("system.algo_trader.schwab.schwab_client.get_logger") as mock_logger_func:
        mock_logger_instance = MagicMock()
        mock_logger_func.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_account_broker():
    """Fixture to mock AccountBroker."""
    with patch("system.algo_trader.schwab.schwab_client.AccountBroker") as mock_broker_class:
        mock_broker = MagicMock()
        mock_broker_class.return_value = mock_broker
        yield mock_broker


@pytest.fixture
def mock_token_manager_requests():
    """Fixture to mock requests module in token_manager."""
    with patch("system.algo_trader.schwab.auth.token_manager.requests") as mock_requests:
        yield mock_requests


@pytest.fixture
def mock_oauth2_requests():
    """Fixture to mock requests module in oauth2."""
    with patch("system.algo_trader.schwab.auth.oauth2.requests") as mock_requests:
        yield mock_requests


@pytest.fixture
def mock_oauth2_input():
    """Fixture to mock input() in oauth2 module."""
    with patch("system.algo_trader.schwab.auth.oauth2.input") as mock_input:
        yield mock_input


@pytest.fixture
def mock_oauth2_print():
    """Fixture to mock print() in oauth2 module."""
    with patch("system.algo_trader.schwab.auth.oauth2.print") as mock_print:
        yield mock_print


@pytest.fixture
def mock_schwab_client_requests():
    """Fixture to mock requests module in schwab_client (for make_authenticated_request)."""
    with patch("system.algo_trader.schwab.schwab_client.requests") as mock_requests:
        yield mock_requests


@pytest.fixture
def mock_token_manager_time():
    """Fixture to mock time.sleep in token_manager."""
    with patch("system.algo_trader.schwab.auth.token_manager.time.sleep") as mock_sleep:
        yield mock_sleep


@pytest.fixture
def mock_dependencies_base(mock_account_broker, mock_logger):
    """Base fixture with common dependencies for SchwabClient tests."""
    return {
        "broker": mock_account_broker,
        "logger": mock_logger,
    }


@pytest.fixture
def mock_dependencies_token_management(mock_dependencies_base, mock_token_manager_requests):
    """Fixture for token management tests."""
    deps = mock_dependencies_base.copy()
    deps["requests"] = mock_token_manager_requests
    return deps


@pytest.fixture
def mock_dependencies_oauth2(
    mock_dependencies_base, mock_oauth2_requests, mock_oauth2_input, mock_oauth2_print
):
    """Fixture for OAuth2 flow tests."""
    deps = mock_dependencies_base.copy()
    deps["requests"] = mock_oauth2_requests
    deps["input"] = mock_oauth2_input
    deps["print"] = mock_oauth2_print
    return deps


@pytest.fixture
def mock_dependencies_utility(mock_dependencies_base, mock_schwab_client_requests):
    """Fixture for utility method tests."""
    deps = mock_dependencies_base.copy()
    deps["requests"] = mock_schwab_client_requests
    return deps


@pytest.fixture
def mock_dependencies_locking(
    mock_dependencies_base,
    mock_token_manager_requests,
    mock_oauth2_input,
    mock_token_manager_time,
):
    """Fixture for distributed locking tests."""
    deps = mock_dependencies_base.copy()
    deps["requests"] = mock_token_manager_requests
    deps["input"] = mock_oauth2_input
    deps["time_sleep"] = mock_token_manager_time
    return deps
