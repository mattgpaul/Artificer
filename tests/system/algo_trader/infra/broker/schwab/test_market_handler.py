"""Unit tests for MarketHandler – Schwab market data API wrapper.

Tests cover:
- URL construction and request delegation
- _send_request success, error, and exception paths
- Quote extraction and higher-level helpers (quotes, price history, hours)
All external dependencies are mocked via ``conftest.py`` fixtures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestMarketHandlerInternal:
    """Tests for internal helpers of MarketHandler."""

    def test_market_url_derived_from_base_url(self, market_handler) -> None:
        """MarketHandler.market_url should be base_url + /marketdata/v1."""
        assert market_handler.market_url == f"{market_handler.base_url}/marketdata/v1"

    def test_send_request_success_returns_json_and_status(
        self,
        market_handler,
        market_handler_request_mock: MagicMock,
    ) -> None:
        """_send_request returns (json, status) when response status is 200."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"ok": True}
        market_handler_request_mock.return_value = response

        data, status = market_handler._send_request("https://example.test", {"a": 1})

        market_handler_request_mock.assert_called_once()
        args, kwargs = market_handler_request_mock.call_args
        assert args[0] == "GET"
        assert args[1] == "https://example.test"
        assert kwargs["params"] == {"a": 1}
        assert data == {"ok": True}
        assert status == 200

    @pytest.mark.parametrize("status_code", [400, 500, 502])
    def test_send_request_non_200_returns_none_and_status(
        self,
        market_handler,
        market_handler_request_mock: MagicMock,
        status_code: int,
    ) -> None:
        """_send_request returns (None, status) when response is not 200."""
        response = MagicMock()
        response.status_code = status_code
        response.text = "error"
        market_handler_request_mock.return_value = response

        data, status = market_handler._send_request("https://example.test", None)

        assert data is None
        assert status == status_code

    def test_send_request_exception_returns_none_none(
        self,
        market_handler,
        market_handler_request_mock: MagicMock,
    ) -> None:
        """_send_request returns (None, None) if make_authenticated_request raises."""
        market_handler_request_mock.side_effect = RuntimeError("boom")

        data, status = market_handler._send_request("https://example.test", None)

        assert data is None
        assert status is None

    def test_extract_quote_data_happy_path(self, market_handler) -> None:
        """_extract_quote_data flattens Schwab quote payload to simple dict."""
        raw: dict[str, Any] = {
            "AAPL": {
                "quote": {
                    "lastPrice": 100.0,
                    "bidPrice": 99.5,
                    "askPrice": 100.5,
                    "totalVolume": 1234,
                    "netChange": 1.0,
                    "netPercentChange": 1.01,
                    "tradeTime": 1700000000,
                }
            }
        }

        extracted = market_handler._extract_quote_data(raw)

        assert extracted["AAPL"]["price"] == 100.0
        assert extracted["AAPL"]["bid"] == 99.5
        assert extracted["AAPL"]["ask"] == 100.5
        assert extracted["AAPL"]["volume"] == 1234
        assert extracted["AAPL"]["change"] == 1.0
        assert extracted["AAPL"]["change_pct"] == 1.01
        assert extracted["AAPL"]["timestamp"] == 1700000000


@pytest.mark.unit
class TestMarketHandlerPublic:
    """Tests for public MarketHandler API methods."""

    def test_get_quotes_success_returns_extracted_data(
        self,
        market_handler,
        market_handler_send_request_mock: MagicMock,
    ) -> None:
        """get_quotes uses _send_request and _extract_quote_data when successful."""
        raw_response = {
            "AAPL": {
                "quote": {
                    "lastPrice": 100.0,
                }
            }
        }
        market_handler_send_request_mock.return_value = (raw_response, 200)

        result = market_handler.get_quotes(["AAPL"])

        market_handler_send_request_mock.assert_called_once()
        args, kwargs = market_handler_send_request_mock.call_args
        assert args[0] == f"{market_handler.market_url}/quotes"
        # params is passed positionally to _send_request
        assert args[1] == {"symbols": "AAPL"}
        # _extract_quote_data should have normalized the payload
        assert result["AAPL"]["price"] == 100.0

    def test_get_quotes_failure_returns_empty_dict(
        self,
        market_handler,
        market_handler_send_request_mock: MagicMock,
    ) -> None:
        """get_quotes returns {} when _send_request returns no response."""
        market_handler_send_request_mock.return_value = (None, 500)

        result = market_handler.get_quotes(["AAPL"])

        assert result == {}

    def test_get_price_history_success_returns_response(
        self,
        market_handler,
        market_handler_send_request_mock: MagicMock,
    ) -> None:
        """get_price_history returns the raw response on success."""
        payload = {"candles": []}
        market_handler_send_request_mock.return_value = (payload, 200)

        result = market_handler.get_price_history("AAPL")

        args, kwargs = market_handler_send_request_mock.call_args
        assert args[0] == f"{market_handler.market_url}/pricehistory"
        # params is passed positionally to _send_request
        params = args[1]
        assert params["symbol"] == "AAPL"
        assert "periodType" in params
        assert "frequencyType" in params
        assert result == payload

    def test_get_price_history_failure_returns_none(
        self,
        market_handler,
        market_handler_send_request_mock: MagicMock,
    ) -> None:
        """get_price_history returns None when _send_request fails."""
        market_handler_send_request_mock.return_value = (None, 500)

        result = market_handler.get_price_history("AAPL")

        assert result is None

    def test_get_option_chains_returns_empty_dict(self, market_handler) -> None:
        """get_option_chains currently returns an empty dict (TODO stub)."""
        assert market_handler.get_option_chains("AAPL") == {}

    def test_get_market_hours_failure_returns_empty_dict(
        self,
        market_handler,
        market_handler_send_request_mock: MagicMock,
    ) -> None:
        """get_market_hours returns {} when _send_request fails."""
        market_handler_send_request_mock.return_value = (None, 500)
        date = datetime(2024, 1, 1)

        result = market_handler.get_market_hours(date)

        assert result == {}

    def test_get_market_hours_equity_EQ_branch(
        self,
        market_handler,
        market_handler_send_request_mock: MagicMock,
    ) -> None:
        """get_market_hours extracts start/end when equity -> EQ is present."""
        date = datetime(2024, 1, 1)
        market_handler_send_request_mock.return_value = (
            {
                "equity": {
                    "EQ": {
                        "isOpen": True,
                        "sessionHours": {
                            "regularMarket": [
                                {"start": "09:30", "end": "16:00"},
                            ]
                        },
                    }
                }
            },
            200,
        )

        result = market_handler.get_market_hours(date)

        assert result["date"] == "2024-01-01"
        assert result["start"] == "09:30"
        assert result["end"] == "16:00"

    def test_get_market_hours_equity_equity_nested_branch(
        self,
        market_handler,
        market_handler_send_request_mock: MagicMock,
    ) -> None:
        """get_market_hours supports equity -> equity nested structure."""
        date = datetime(2024, 1, 1)
        market_handler_send_request_mock.return_value = (
            {
                "equity": {
                    "equity": {
                        "isOpen": True,
                        "sessionHours": {
                            "regularMarket": [
                                {"start": "09:30", "end": "16:00"},
                            ]
                        },
                    }
                }
            },
            200,
        )

        result = market_handler.get_market_hours(date)

        assert result["date"] == "2024-01-01"
        assert result["start"] == "09:30"
        assert result["end"] == "16:00"

    def test_get_market_hours_no_equity_returns_date_only(
        self,
        market_handler,
        market_handler_send_request_mock: MagicMock,
    ) -> None:
        """get_market_hours returns only date when no equity data is present."""
        date = datetime(2024, 1, 1)
        market_handler_send_request_mock.return_value = ({"other": {}}, 200)

        result = market_handler.get_market_hours(date)

        assert result == {"date": "2024-01-01"}


