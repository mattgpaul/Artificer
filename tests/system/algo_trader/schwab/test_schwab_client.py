"""Unit tests for SchwabClient – auth headers and HTTP adapter behavior.

These tests follow the same pattern as the Redis client tests:
- All external dependencies are mocked in ``conftest.py``
- Tests only assert contracts on the public API of ``SchwabClient``.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.unit
class TestSchwabClient:
    """Contract tests for SchwabClient authentication behavior."""

    def test_get_auth_headers_uses_token_manager(
        self,
        schwab_client,
        token_manager_mock: dict[str, Any],
    ) -> None:
        """``get_auth_headers`` should delegate to TokenManager and format headers."""
        token_manager_mock["instance"].get_valid_access_token.return_value = "abc123"

        headers = schwab_client.get_auth_headers()

        token_manager_mock["instance"].get_valid_access_token.assert_called_once()
        assert headers["Authorization"] == "Bearer abc123"
        assert headers["Accept"] == "application/json"

    def test_make_authenticated_request_merges_headers(
        self,
        schwab_client,
        token_manager_mock: dict[str, Any],
        requests_mock,
    ) -> None:
        """``make_authenticated_request`` should merge auth and caller headers."""
        token_manager_mock["instance"].get_valid_access_token.return_value = "token-xyz"

        # Configure the mocked requests.request return value
        response_obj = object()
        requests_mock.request.return_value = response_obj

        response = schwab_client.make_authenticated_request(
            "GET",
            "https://example.test/resource",
            headers={"X-Custom": "value"},
        )

        # We receive the mocked response
        assert response is response_obj

        # requests.request was called with merged headers
        requests_mock.request.assert_called_once()
        method, url = requests_mock.request.call_args[0][:2]
        kwargs = requests_mock.request.call_args[1]

        assert method == "GET"
        assert url == "https://example.test/resource"

        sent_headers = kwargs["headers"]
        assert sent_headers["Authorization"] == "Bearer token-xyz"
        assert sent_headers["Accept"] == "application/json"
        assert sent_headers["X-Custom"] == "value"
