"""Shared fixtures for Schwab client tests.

All external dependencies (env, token manager, HTTP) are mocked here so
individual tests only assert behavior and contracts, similar to the Redis
infrastructure tests.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def schwab_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure Schwab env vars are set for all Schwab tests.

    SchwabBase validates that SCHWAB_API_KEY, SCHWAB_SECRET, and SCHWAB_APP_NAME
    are present. For unit tests we provide deterministic dummy values.
    """
    monkeypatch.setenv("SCHWAB_API_KEY", "test-api-key")
    monkeypatch.setenv("SCHWAB_SECRET", "test-secret")
    monkeypatch.setenv("SCHWAB_APP_NAME", "test-app")
    monkeypatch.setenv("SCHWAB_REFRESH_TOKEN", "test-refresh-token")


@pytest.fixture
def token_manager_mock() -> dict[str, Any]:
    """Patch TokenManager used inside SchwabClient.

    Provides access to both the patched class and the constructed instance so
    tests can assert interactions without touching real token logic.
    """
    with patch("system.algo_trader.schwab.schwab_client.TokenManager") as MockTM:
        instance = MagicMock()
        MockTM.return_value = instance
        yield {"class": MockTM, "instance": instance}


@pytest.fixture
def requests_mock() -> MagicMock:
    """Patch the requests module used in SchwabClient.

    Tests can inspect calls to ``requests.request`` and control its return
    value without performing real HTTP.
    """
    with patch("system.algo_trader.schwab.schwab_client.requests") as mock_requests:
        # Ensure the expected API exists for type checkers and tests
        mock_requests.request = MagicMock()
        yield mock_requests


@pytest.fixture
def schwab_client(
    token_manager_mock: dict[str, Any],  # noqa: ARG001
    requests_mock: MagicMock,  # noqa: ARG001
):
    """Provide a SchwabClient instance wired to patched dependencies."""
    # Import here to avoid circular import issues at module import time
    from system.algo_trader.schwab.schwab_client import SchwabClient

    return SchwabClient()


@pytest.fixture
def account_handler():
    """Provide an AccountHandler instance with real config but mocked HTTP.

    The underlying ``make_authenticated_request`` method is replaced with a
    ``MagicMock`` so tests can control responses and assert call contracts
    without performing real network I/O.
    """
    from system.algo_trader.schwab.account_handler import AccountHandler

    handler = AccountHandler()
    return handler


@pytest.fixture
def account_handler_request_mock(account_handler) -> MagicMock:
    """Attach and return a MagicMock for AccountHandler.make_authenticated_request."""
    request_mock: MagicMock = MagicMock()
    # Patch the bound method on this instance only; we don't touch the class.
    account_handler.make_authenticated_request = request_mock
    return request_mock


@pytest.fixture
def market_handler():
    """Provide a MarketHandler instance with real config but mocked HTTP."""
    from system.algo_trader.schwab.market_handler import MarketHandler

    handler = MarketHandler()
    return handler


@pytest.fixture
def market_handler_request_mock(market_handler) -> MagicMock:
    """Attach and return a MagicMock for MarketHandler.make_authenticated_request."""
    request_mock: MagicMock = MagicMock()
    market_handler.make_authenticated_request = request_mock
    return request_mock


@pytest.fixture
def market_handler_send_request_mock(market_handler) -> MagicMock:
    """Attach and return a MagicMock for MarketHandler._send_request."""
    send_request_mock: MagicMock = MagicMock()
    market_handler._send_request = send_request_mock
    return send_request_mock


@pytest.fixture
def token_manager_fixtures():
    """Provide a TokenManager instance with patched dependencies for unit tests.

    Patches:
    - AccountBroker to avoid real Redis
    - requests module to avoid real HTTP
    - time module to avoid real sleeping
    """
    with (
        patch("system.algo_trader.schwab.token_manager.AccountBroker") as BrokerCls,
        patch("system.algo_trader.schwab.token_manager.requests") as requests_mod,
        patch("system.algo_trader.schwab.token_manager.time") as time_mod,
    ):
        broker = MagicMock()
        BrokerCls.return_value = broker
        time_mod.sleep = MagicMock()

        from system.algo_trader.schwab.token_manager import TokenManager

        manager = TokenManager()
        oauth2_handler = MagicMock()
        refresh_mock = MagicMock()

        # Attach mocks to the manager instance for tests to configure.
        manager.oauth2_handler = oauth2_handler
        manager.refresh_token = refresh_mock

        yield {
            "manager": manager,
            "broker": broker,
            "requests": requests_mod,
            "time": time_mod,
            "oauth2_handler": oauth2_handler,
            "refresh_mock": refresh_mock,
        }


@pytest.fixture
def token_manager_refresh_fixtures():
    """Provide TokenManager and dependencies for refresh/_load_token_from_config tests."""
    with (
        patch("system.algo_trader.schwab.token_manager.AccountBroker") as BrokerCls,
        patch("system.algo_trader.schwab.token_manager.requests") as requests_mod,
    ):
        broker = MagicMock()
        BrokerCls.return_value = broker

        from system.algo_trader.schwab.token_manager import TokenManager

        manager = TokenManager()
        manager.oauth2_handler = MagicMock()

        yield {
            "manager": manager,
            "broker": broker,
            "requests": requests_mod,
        }


@pytest.fixture
def oauth2_requests_mock() -> MagicMock:
    """Patch the requests module used in OAuth2Handler."""
    with patch("system.algo_trader.schwab.oauth2_handler.requests") as mock_requests:
        yield mock_requests


@pytest.fixture
def input_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch builtins.input with a MagicMock for interactive flows."""
    mock = MagicMock()
    monkeypatch.setattr("builtins.input", mock)
    return mock


@pytest.fixture
def oauth2_handler(oauth2_requests_mock: MagicMock):
    """Provide an OAuth2Handler instance with patched HTTP and broker."""
    from system.algo_trader.schwab.oauth2_handler import OAuth2Handler

    handler = OAuth2Handler()
    handler.account_broker = MagicMock()
    return handler


@pytest.fixture
def oauth2_handler_with_mocks(oauth2_handler):
    """Provide OAuth2Handler plus MagicMocks for internal helpers.

    Used by authenticate() tests to assert interactions without exercising the
    underlying HTTP/token logic again.
    """
    exchange_mock = MagicMock()
    display_mock = MagicMock()
    oauth2_handler._exchange_code_for_tokens = exchange_mock
    oauth2_handler._display_refresh_token_instructions = display_mock
    return {
        "handler": oauth2_handler,
        "exchange_mock": exchange_mock,
        "display_mock": display_mock,
    }

