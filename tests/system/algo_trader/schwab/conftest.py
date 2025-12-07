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

