"""Unit tests for AccountHandler – Schwab account API wrapper.

Tests cover URL construction, HTTP delegation via ``make_authenticated_request``,
and basic success/error handling for the public AccountHandler methods.
All external dependencies (config, HTTP, tokens) are mocked via ``conftest.py``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestAccountHandler:
    """Contract tests for AccountHandler account/position/order operations."""

    def test_account_url_derived_from_base_url(self, account_handler) -> None:
        """AccountHandler.account_url should be base_url + /trader/v1."""
        assert account_handler.account_url == f"{account_handler.base_url}/trader/v1"

    def test_get_accounts_success(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """get_accounts delegates to make_authenticated_request and returns JSON on 200."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"accounts": [{"id": "1"}]}
        account_handler_request_mock.return_value = response

        result = account_handler.get_accounts()

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "GET"
        assert url == f"{account_handler.account_url}/accounts"
        assert result == {"accounts": [{"id": "1"}]}

    def test_get_accounts_failure_returns_empty_dict(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """Non-200 status from get_accounts should return an empty dict."""
        response = MagicMock()
        response.status_code = 500
        response.text = "Server error"
        account_handler_request_mock.return_value = response

        result = account_handler.get_accounts()

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "GET"
        assert url == f"{account_handler.account_url}/accounts"
        assert result == {}

    def test_get_account_details_success(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """get_account_details returns JSON on 200 for a specific account."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": "1234"}
        account_handler_request_mock.return_value = response

        result = account_handler.get_account_details("1234")

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "GET"
        assert url == f"{account_handler.account_url}/accounts/1234"
        assert result == {"id": "1234"}

    def test_get_account_details_failure_returns_empty_dict(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """Non-200 status from get_account_details should return an empty dict."""
        response = MagicMock()
        response.status_code = 404
        response.text = "Not found"
        account_handler_request_mock.return_value = response

        result = account_handler.get_account_details("missing")

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "GET"
        assert url == f"{account_handler.account_url}/accounts/missing"
        assert result == {}

    def test_get_positions_success(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """get_positions returns JSON on 200 for a specific account."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"positions": [{"symbol": "AAPL"}]}
        account_handler_request_mock.return_value = response

        result = account_handler.get_positions("acct-1")

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "GET"
        assert url == f"{account_handler.account_url}/accounts/acct-1/positions"
        assert result == {"positions": [{"symbol": "AAPL"}]}

    def test_get_positions_failure_returns_empty_dict(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """Non-200 status from get_positions should return an empty dict."""
        response = MagicMock()
        response.status_code = 400
        response.text = "Bad request"
        account_handler_request_mock.return_value = response

        result = account_handler.get_positions("acct-1")

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "GET"
        assert url == f"{account_handler.account_url}/accounts/acct-1/positions"
        assert result == {}

    def test_get_orders_success(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """get_orders returns JSON on 200 for a specific account."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"orders": [{"id": "ord-1"}]}
        account_handler_request_mock.return_value = response

        result = account_handler.get_orders("acct-1")

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "GET"
        assert url == f"{account_handler.account_url}/accounts/acct-1/orders"
        assert result == {"orders": [{"id": "ord-1"}]}

    def test_get_orders_failure_returns_empty_dict(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """Non-200 status from get_orders should return an empty dict."""
        response = MagicMock()
        response.status_code = 403
        response.text = "Forbidden"
        account_handler_request_mock.return_value = response

        result = account_handler.get_orders("acct-1")

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "GET"
        assert url == f"{account_handler.account_url}/accounts/acct-1/orders"
        assert result == {}

    @pytest.mark.parametrize("status_code", [200, 201])
    def test_place_order_success_status_codes(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
        status_code: int,
    ) -> None:
        """place_order should treat 200 and 201 as success and return JSON."""
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = {"orderId": "ord-1"}
        account_handler_request_mock.return_value = response

        payload: dict[str, Any] = {"symbol": "AAPL", "qty": 1}
        result = account_handler.place_order("acct-1", payload)

        method, url = account_handler_request_mock.call_args[0][:2]
        kwargs = account_handler_request_mock.call_args[1]

        assert method == "POST"
        assert url == f"{account_handler.account_url}/accounts/acct-1/orders"
        assert kwargs["json"] is payload
        assert result == {"orderId": "ord-1"}

    def test_place_order_failure_returns_empty_dict(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
    ) -> None:
        """Non-200/201 status from place_order should return an empty dict."""
        response = MagicMock()
        response.status_code = 400
        response.text = "Bad request"
        account_handler_request_mock.return_value = response

        result = account_handler.place_order("acct-1", {"symbol": "AAPL"})

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "POST"
        assert url == f"{account_handler.account_url}/accounts/acct-1/orders"
        assert result == {}

    @pytest.mark.parametrize(
        "status_code, expected",
        [
            (200, True),
            (500, False),
        ],
    )
    def test_cancel_order_status_mapping(
        self,
        account_handler,
        account_handler_request_mock: MagicMock,
        status_code: int,
        expected: bool,
    ) -> None:
        """cancel_order should return True only on 200, otherwise False."""
        response = MagicMock()
        response.status_code = status_code
        response.text = "msg"
        account_handler_request_mock.return_value = response

        result = account_handler.cancel_order("acct-1", "ord-1")

        method, url = account_handler_request_mock.call_args[0][:2]
        assert method == "DELETE"
        assert url == f"{account_handler.account_url}/accounts/acct-1/orders/ord-1"
        assert result is expected


