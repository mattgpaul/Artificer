"""Unit tests for Tickers - SEC Ticker Data Retrieval.

Tests cover successful data retrieval, error handling, rate limiting, and
network failure scenarios. All external dependencies are mocked via conftest.py.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestTickersInitialization:
    """Test Tickers initialization."""

    def test_initialization_success(self, tickers):
        """Test Tickers initializes correctly."""
        assert tickers is not None
        assert hasattr(tickers, "logger")


class TestGetTickersSuccess:
    """Test successful ticker data retrieval."""

    def test_get_tickers_success(self, tickers, mock_http_response):
        """Test successful retrieval of ticker data from SEC."""
        mock_response_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
        }

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(
                status_code=200, content_type="application/json", json_data=mock_response_data
            )
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
        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()


class TestGetTickersErrorHandling:
    """Test error handling for various failure scenarios."""

    @pytest.mark.parametrize(
        "status_code,content_type,text_content,should_log_info",
        [
            (404, "text/plain", "Not Found", True),
            (500, "text/html", "Internal Server Error", True),
        ],
    )
    def test_get_tickers_http_errors(
        self, tickers, mock_http_response, status_code, content_type, text_content, should_log_info
    ):
        """Test get_tickers handles various HTTP error status codes."""
        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(
                status_code=status_code, content_type=content_type, text=text_content
            )
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()
            if should_log_info:
                tickers.logger.info.assert_called()

    def test_get_tickers_non_200_status_code(self, tickers, mock_http_response):
        """Test get_tickers handles non-200 HTTP status codes."""
        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(status_code=404, text="Not Found")
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()
            # Verify response preview was logged
            tickers.logger.info.assert_called()
            log_call = str(tickers.logger.info.call_args)
            assert "Not Found" in log_call

    def test_get_tickers_html_response_instead_of_json(self, tickers, mock_http_response):
        """Test get_tickers handles HTML response (e.g., rate limiting page)."""
        html_content = "<html><body>Rate Limit Exceeded</body></html>"

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(
                status_code=200, content_type="text/html", text=html_content
            )
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()
            # Verify response preview was logged
            tickers.logger.info.assert_called()
            log_call = str(tickers.logger.info.call_args)
            assert html_content in log_call

    def test_get_tickers_no_content_type(self, tickers, mock_http_response):
        """Test get_tickers handles missing Content-Type header."""
        mock_response_data = {"test": "data"}

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            # Create response with empty headers
            mock_response = mock_http_response(
                status_code=200, content_type="", json_data=mock_response_data
            )
            mock_response.headers = {}  # No Content-Type header
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()

    def test_get_tickers_json_decode_error(self, tickers):
        """Test get_tickers handles JSON decode errors."""
        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
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

    def test_get_tickers_sec_rate_limit_response(self, tickers, mock_http_response):
        """Test get_tickers handles SEC rate limiting HTML page."""
        rate_limit_html = (
            "<!DOCTYPE html>"
            "<html><head><title>Request Rate Threshold Exceeded</title></head>"
            "<body><h1>Automated access to our sites...</h1></body></html>"
        )

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(
                status_code=200, content_type="text/html", text=rate_limit_html
            )
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result is None
            tickers.logger.error.assert_called()
            # Verify the rate limit content was logged
            log_call = str(tickers.logger.info.call_args)
            assert "Request Rate Threshold Exceeded" in log_call or "rate_limit_html" in log_call

    def test_get_tickers_with_proper_headers(self, tickers, mock_http_response):
        """Test that proper headers are sent to SEC API."""
        mock_response_data = {"test": "data"}

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(
                status_code=200, content_type="application/json", json_data=mock_response_data
            )
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

    @pytest.mark.parametrize(
        "content_type,should_succeed",
        [
            ("application/json", True),
            ("application/json; charset=utf-8", True),
            ("text/json", True),
            ("application/vnd.api+json", True),
            ("text/html", False),
            ("text/plain", False),
            ("application/xml", False),
            ("image/png", False),
            ("", False),
        ],
    )
    def test_content_type_validation(
        self, tickers, mock_http_response, content_type, should_succeed
    ):
        """Test that content type validation works correctly."""
        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            if should_succeed:
                mock_response = mock_http_response(
                    status_code=200, content_type=content_type, json_data={"data": "test"}
                )
            else:
                mock_response = mock_http_response(status_code=200, content_type=content_type)
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            if should_succeed:
                assert result is not None
            else:
                assert result is None


class TestGetTickersEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_response(self, tickers, mock_http_response):
        """Test handling of empty response."""
        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(
                status_code=200, content_type="application/json", json_data={}
            )
            mock_get.return_value = mock_response

            result = tickers.get_tickers()

            assert result == {}

    def test_large_response_preview_logged(self, tickers, mock_http_response):
        """Test that only first 500 characters of error response are logged."""
        large_response = "x" * 1000

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(status_code=500, text=large_response)
            mock_get.return_value = mock_response

            tickers.get_tickers()

            # Verify only 500 chars were logged
            tickers.logger.info.assert_called()
            logged_text = str(tickers.logger.info.call_args)
            # The preview should be limited
            assert len(logged_text) < 1000


class TestGetCikFromTicker:
    """Test CIK retrieval from ticker symbol."""

    def test_get_cik_from_ticker_success(self, tickers):
        """Test successful CIK retrieval from ticker."""
        mock_tickers_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
        }

        with patch.object(tickers, "get_tickers", return_value=mock_tickers_data):
            cik = tickers._get_cik_from_ticker("AAPL")

            assert cik == "0000320193"
            assert tickers._ticker_to_cik_cache["AAPL"] == "0000320193"

    def test_get_cik_from_ticker_cached(self, tickers):
        """Test CIK retrieval uses cache."""
        tickers._ticker_to_cik_cache["AAPL"] = "0000320193"

        with patch.object(tickers, "get_tickers") as mock_get_tickers:
            cik = tickers._get_cik_from_ticker("AAPL")

            assert cik == "0000320193"
            mock_get_tickers.assert_not_called()

    def test_get_cik_from_ticker_not_found(self, tickers):
        """Test CIK retrieval when ticker not found."""
        mock_tickers_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        }

        with patch.object(tickers, "get_tickers", return_value=mock_tickers_data):
            cik = tickers._get_cik_from_ticker("INVALID")

            assert cik is None
            tickers.logger.error.assert_called()

    def test_get_cik_from_ticker_get_tickers_fails(self, tickers):
        """Test CIK retrieval when get_tickers returns None."""
        with patch.object(tickers, "get_tickers", return_value=None):
            cik = tickers._get_cik_from_ticker("AAPL")

            assert cik is None


class TestFetchCompanyFacts:
    """Test company facts fetching from SEC API."""

    def test_fetch_company_facts_success(self, tickers_with_mocked_time, mock_http_response):
        """Test successful company facts fetch."""
        tickers = tickers_with_mocked_time
        cik = "0000320193"
        mock_facts = {"entityName": "Apple Inc.", "facts": {}}

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(
                status_code=200, content_type="application/json", json_data=mock_facts
            )
            mock_get.return_value = mock_response

            result = tickers._fetch_company_facts(cik)

            assert result == mock_facts
            assert cik in tickers._company_facts_cache

    def test_fetch_company_facts_uses_cache(self, tickers_with_mocked_time):
        """Test company facts uses cache when available and fresh."""
        tickers = tickers_with_mocked_time
        cik = "0000320193"
        mock_facts = {"entityName": "Apple Inc."}
        tickers._company_facts_cache[cik] = (mock_facts, 1000000.0 - 3600)  # 1 hour ago

        result = tickers._fetch_company_facts(cik, use_cache=True)

        assert result == mock_facts
        tickers.logger.debug.assert_called()

    def test_fetch_company_facts_cache_expired(self, tickers_with_mocked_time, mock_http_response):
        """Test company facts refetches when cache is expired."""
        tickers = tickers_with_mocked_time
        cik = "0000320193"
        old_facts = {"entityName": "Old Name"}
        new_facts = {"entityName": "New Name"}

        # Cache is 25 hours old
        tickers._company_facts_cache[cik] = (old_facts, 1000000.0 - 25 * 3600)

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(
                status_code=200, content_type="application/json", json_data=new_facts
            )
            mock_get.return_value = mock_response

            result = tickers._fetch_company_facts(cik, use_cache=True)

            assert result == new_facts

    def test_fetch_company_facts_http_error(self, tickers, mock_http_response):
        """Test company facts handles HTTP errors."""
        cik = "0000320193"

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_response = mock_http_response(status_code=404)
            mock_get.return_value = mock_response

            result = tickers._fetch_company_facts(cik)

            assert result is None
            tickers.logger.error.assert_called()

    def test_fetch_company_facts_exception(self, tickers):
        """Test company facts handles exceptions."""
        cik = "0000320193"

        with patch("system.algo_trader.datasource.sec.tickers.main.requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = tickers._fetch_company_facts(cik)

            assert result is None
            tickers.logger.error.assert_called()


class TestExtractAllPeriodsForFact:
    """Test period extraction from company facts."""

    def test_extract_periods_success(self, tickers):
        """Test successful period extraction."""
        period_end = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {
                                    "end": period_end,
                                    "val": 1000000,
                                    "fp": "Q1",
                                }
                            ]
                        }
                    }
                }
            }
        }

        periods = tickers._dataframe_builder._extract_all_periods_for_fact(
            facts, "Revenues", years_back=10, require_quarterly=True
        )

        assert len(periods) == 1
        assert periods[0]["value"] == 1000000
        assert periods[0]["unit"] == "USD"

    def test_extract_periods_namespace_not_found(self, tickers):
        """Test period extraction when namespace not found."""
        facts = {"facts": {}}

        periods = tickers._dataframe_builder._extract_all_periods_for_fact(
            facts, "Revenues", years_back=10, require_quarterly=True
        )

        assert periods == []
        tickers.logger.debug.assert_called()

    def test_extract_periods_fact_not_found(self, tickers):
        """Test period extraction when fact not found."""
        facts = {"facts": {"us-gaap": {}}}

        periods = tickers._dataframe_builder._extract_all_periods_for_fact(
            facts, "Revenues", years_back=10, require_quarterly=True
        )

        assert periods == []
        tickers.logger.debug.assert_called()

    def test_extract_periods_filters_old_periods(self, tickers):
        """Test period extraction filters out old periods."""
        old_period = (
            (datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year - 15))
            .isoformat()
            .replace("+00:00", "Z")
        )
        recent_period = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"end": old_period, "val": 1000000, "fp": "Q1"},
                                {"end": recent_period, "val": 2000000, "fp": "Q1"},
                            ]
                        }
                    }
                }
            }
        }

        periods = tickers._dataframe_builder._extract_all_periods_for_fact(
            facts, "Revenues", years_back=10, require_quarterly=True
        )

        assert len(periods) == 1
        assert periods[0]["value"] == 2000000

    def test_extract_periods_filters_non_quarterly(self, tickers):
        """Test period extraction filters out non-quarterly periods."""
        period_end = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"end": period_end, "val": 1000000, "fp": "Q1"},
                                {"end": period_end, "val": 2000000, "fp": "FY"},
                            ]
                        }
                    }
                }
            }
        }

        periods = tickers._dataframe_builder._extract_all_periods_for_fact(
            facts, "Revenues", years_back=10, require_quarterly=True
        )

        assert len(periods) == 1
        assert periods[0]["value"] == 1000000


class TestBuildTimeSeriesDataframe:
    """Test time series DataFrame building."""

    def test_build_time_series_dataframe_success(self, tickers):
        """Test successful time series DataFrame building."""
        period_end = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"end": period_end, "val": 1000000, "fp": "Q1"},
                            ]
                        }
                    }
                }
            }
        }

        df = tickers._dataframe_builder.build_time_series_dataframe(facts, "AAPL", years_back=10)

        assert isinstance(df, pd.DataFrame)
        assert "ticker" in df.columns
        assert len(df) > 0

    def test_build_time_series_dataframe_empty(self, tickers):
        """Test time series DataFrame building with no data."""
        facts = {"facts": {}}

        df = tickers._dataframe_builder.build_time_series_dataframe(facts, "AAPL", years_back=10)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestExtractStaticInfo:
    """Test static information extraction."""

    def test_extract_static_info_success(self, tickers):
        """Test successful static info extraction."""
        facts = {
            "entityName": "Apple Inc.",
            "sic": "3571",
            "sicDescription": "Electronic Computers",
        }

        static_info = tickers._static_extractor.extract_static_info(facts, "AAPL")

        assert static_info["ticker"] == "AAPL"
        assert static_info["entity_name"] == "Apple Inc."
        assert static_info["sic"] == "3571"
        assert static_info["industry"] == "Electronic Computers"

    def test_extract_static_info_missing_fields(self, tickers):
        """Test static info extraction with missing fields."""
        facts = {"entityName": "Apple Inc."}

        static_info = tickers._static_extractor.extract_static_info(facts, "AAPL")

        assert static_info["ticker"] == "AAPL"
        assert static_info["entity_name"] == "Apple Inc."
        assert static_info["sic"] is None
        assert static_info["industry"] is None


class TestGetCompanyFacts:
    """Test get_company_facts public method."""

    def test_get_company_facts_success(self, tickers):
        """Test successful company facts retrieval."""
        mock_tickers_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        }
        period_end = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        mock_facts = {
            "entityName": "Apple Inc.",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"end": period_end, "val": 1000000, "fp": "Q1"},
                            ]
                        }
                    }
                }
            },
        }

        with (
            patch.object(tickers, "get_tickers", return_value=mock_tickers_data),
            patch.object(tickers, "_fetch_company_facts", return_value=mock_facts),
        ):
            result = tickers.get_company_facts("AAPL")

            assert result is not None
            assert "static" in result
            assert "time_series" in result
            assert result["static"]["ticker"] == "AAPL"

    def test_get_company_facts_cik_not_found(self, tickers):
        """Test company facts when CIK not found."""
        with patch.object(tickers, "_get_cik_from_ticker", return_value=None):
            result = tickers.get_company_facts("INVALID")

            assert result is None

    def test_get_company_facts_fetch_fails(self, tickers):
        """Test company facts when fetch fails."""
        with (
            patch.object(tickers, "_get_cik_from_ticker", return_value="0000320193"),
            patch.object(tickers, "_fetch_company_facts", return_value=None),
        ):
            result = tickers.get_company_facts("AAPL")

            assert result is None
