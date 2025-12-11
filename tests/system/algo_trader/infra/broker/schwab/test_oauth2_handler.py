"""Unit tests for OAuth2Handler – Schwab OAuth2 authorization flow.

Tests focus on:
- _exchange_code_for_tokens happy path and error path
- authenticate flow with valid and invalid redirect URLs
All external dependencies (requests, AccountBroker, input) are mocked via
fixtures in ``conftest.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestOAuth2HandlerInit:
    """Construction-time behavior for OAuth2Handler."""

    def test_default_constructor_initializes_account_broker(self) -> None:
        """OAuth2Handler() should create an AccountBroker for token persistence.

        This guards the CLI path used by the ``authenticate`` Bazel binary,
        where OAuth2Handler is instantiated directly without test fixtures.
        """
        from system.algo_trader.infra.broker.schwab.oauth2_handler import OAuth2Handler

        with patch(
            "system.algo_trader.schwab.oauth2_handler.AccountBroker"
        ) as BrokerCls:
            broker_instance = MagicMock()
            BrokerCls.return_value = broker_instance

            handler = OAuth2Handler()

        assert handler.account_broker is broker_instance


@pytest.mark.unit
class TestOAuth2HandlerExchange:
    """Tests for OAuth2Handler._exchange_code_for_tokens."""

    def test_exchange_code_for_tokens_success(
        self,
        oauth2_requests_mock,
        oauth2_handler,
    ) -> None:
        """HTTP 200 should return parsed JSON token payload."""
        response = oauth2_requests_mock.post.return_value
        response.status_code = 200
        response.json.return_value = {"access_token": "abc", "refresh_token": "rt"}

        tokens = oauth2_handler._exchange_code_for_tokens("code-123")

        assert tokens == {"access_token": "abc", "refresh_token": "rt"}
        oauth2_requests_mock.post.assert_called_once()

    def test_exchange_code_for_tokens_failure_logs_and_returns_none(
        self,
        oauth2_requests_mock,
        oauth2_handler,
    ) -> None:
        """Non-200 HTTP status should log error and return None."""
        response = oauth2_requests_mock.post.return_value
        response.status_code = 400
        response.text = "Bad Request"

        tokens = oauth2_handler._exchange_code_for_tokens("code-123")

        assert tokens is None


@pytest.mark.unit
class TestOAuth2HandlerAuthenticate:
    """Tests for OAuth2Handler.authenticate interactive flow."""

    def test_authenticate_invalid_redirect_url_returns_none(
        self,
        oauth2_handler_with_mocks,
        input_mock,
    ) -> None:
        """If redirect URL is missing 'code=', authenticate should return None."""
        handler = oauth2_handler_with_mocks["handler"]
        input_mock.return_value = "https://example.test/redirect?state=xyz"

        result = handler.authenticate()

        assert result is None
        oauth2_handler_with_mocks["exchange_mock"].assert_not_called()

    def test_authenticate_happy_path_stores_tokens_and_returns_payload(
        self,
        oauth2_handler_with_mocks,
        input_mock,
    ) -> None:
        """Valid redirect URL should trigger token exchange and storage."""
        handler = oauth2_handler_with_mocks["handler"]
        exchange_mock = oauth2_handler_with_mocks["exchange_mock"]
        display_mock = oauth2_handler_with_mocks["display_mock"]

        # URL contains "code=AUTHCODE%40" to simulate Schwab redirect format
        input_mock.return_value = (
            "https://redirect.test/callback?state=xyz&code=AUTHCODE%40some-suffix"
        )

        exchange_mock.return_value = {
            "access_token": "access-123",
            "refresh_token": "refresh-456",
        }

        result = handler.authenticate()

        # Code fragment extracted should be "AUTHCODE@"
        exchange_mock.assert_called_once_with("AUTHCODE@")

        broker = handler.account_broker
        broker.set_access_token.assert_called_once_with("access-123")
        broker.set_refresh_token.assert_called_once_with("refresh-456")

        display_mock.assert_called_once_with("refresh-456")

        assert result == {
            "access_token": "access-123",
            "refresh_token": "refresh-456",
        }


