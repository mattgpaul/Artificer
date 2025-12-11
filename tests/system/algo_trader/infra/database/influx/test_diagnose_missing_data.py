"""Unit tests for diagnose_missing_data - Diagnostic Script.

Tests cover diagnostic functions for checking Redis queues, InfluxDB contents,
bad tickers, and data format issues. All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import pandas as pd

from system.algo_trader.influx.diagnose_missing_data import (
    check_bad_tickers,
    check_data_format_issue,
    check_influxdb_tickers,
    check_redis_queue,
    get_sec_registry_tickers,
    main,
)
from system.algo_trader.influx.market_data_influx import MarketDataInflux


class TestCheckRedisQueue:
    """Test Redis queue checking functionality."""

    def test_check_redis_queue_empty_queue(self, mock_queue_broker):
        """Test checking empty Redis queue."""
        mock_queue_broker.get_queue_size.return_value = 0
        mock_queue_broker.peek_queue.return_value = []

        result = check_redis_queue(mock_queue_broker)

        assert result["queue_name"] == "ohlcv_queue"
        assert result["size"] == 0
        assert result["sample_items"] == []
        assert result["sample_data"] == []

    def test_check_redis_queue_with_items(self, mock_queue_broker):
        """Test checking Redis queue with items."""
        mock_queue_broker.get_queue_size.return_value = 2
        mock_queue_broker.peek_queue.return_value = ["item1", "item2"]
        mock_queue_broker.get_data.side_effect = [
            {
                "ticker": "AAPL",
                "candles": [
                    {"datetime": 1609459200000, "open": 100.0, "close": 104.0},
                    {"datetime": 1609545600000, "open": 101.0, "close": 105.0},
                ],
            },
            {"ticker": "TSLA", "candles": []},
        ]

        result = check_redis_queue(mock_queue_broker)

        assert result["size"] == 2
        assert len(result["sample_items"]) == 2
        assert len(result["sample_data"]) == 2
        assert result["sample_data"][0]["ticker"] == "AAPL"
        assert result["sample_data"][0]["candles_count"] == 2

    def test_check_redis_queue_missing_candles_key(self, mock_queue_broker):
        """Test checking queue item without candles key."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.peek_queue.return_value = ["item1"]
        mock_queue_broker.get_data.return_value = {"ticker": "AAPL"}

        result = check_redis_queue(mock_queue_broker)

        assert result["sample_data"][0]["has_candles"] is False
        assert result["sample_data"][0]["candles_type"] is None

    def test_check_redis_queue_invalid_candles_type(self, mock_queue_broker):
        """Test checking queue item with invalid candles type."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.peek_queue.return_value = ["item1"]
        mock_queue_broker.get_data.return_value = {"ticker": "AAPL", "candles": "not_a_list"}

        result = check_redis_queue(mock_queue_broker)

        assert result["sample_data"][0]["candles_structure"] == "not a list"


class TestCheckInfluxDBTickers:
    """Test InfluxDB ticker checking functionality."""

    def test_check_influxdb_tickers_success(self, mock_influx_dependencies):
        """Test successful InfluxDB ticker query."""
        mock_df = pd.DataFrame({"ticker": ["AAPL", "MSFT", "GOOGL"]})
        mock_influx_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()
        result = check_influxdb_tickers(client)

        assert result["ticker_count"] == 3
        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]
        assert "GOOGL" in result["tickers"]

    def test_check_influxdb_tickers_empty_result(self, mock_influx_dependencies):
        """Test InfluxDB query with empty result."""
        mock_df = pd.DataFrame()
        mock_influx_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()
        result = check_influxdb_tickers(client)

        assert result["ticker_count"] == 0
        assert result["tickers"] == []

    def test_check_influxdb_tickers_false_result(self, mock_influx_dependencies):
        """Test InfluxDB query returning False."""
        mock_influx_dependencies["client"].query.return_value = False

        client = MarketDataInflux()
        result = check_influxdb_tickers(client)

        assert result["ticker_count"] == 0
        assert result["tickers"] == []

    def test_check_influxdb_tickers_query_error(self, mock_influx_dependencies):
        """Test InfluxDB query with exception."""
        client = MarketDataInflux()
        # Mock query to raise exception
        client.query = lambda q: (_ for _ in ()).throw(Exception("Query failed"))

        result = check_influxdb_tickers(client)

        assert "error" in result
        assert "Query failed" in result["error"]


class TestCheckBadTickers:
    """Test bad ticker checking functionality."""

    def test_check_bad_tickers_success(self, mock_diagnose_bad_ticker_client):
        """Test successful bad ticker retrieval."""
        mock_diagnose_bad_ticker_client.get_bad_tickers.return_value = [
            {"ticker": "BAD1", "timestamp": "2024-01-01", "reason": "Invalid"},
            {"ticker": "BAD2", "timestamp": "2024-01-02", "reason": "Error"},
        ]

        result = check_bad_tickers()

        assert result["count"] == 2
        assert "BAD1" in result["tickers"]
        assert "BAD2" in result["tickers"]

    def test_check_bad_tickers_error(self, mock_diagnose_bad_ticker_client):
        """Test bad ticker check with error."""
        mock_diagnose_bad_ticker_client.get_bad_tickers.side_effect = Exception("DB error")

        result = check_bad_tickers()

        assert "error" in result
        assert "DB error" in result["error"]


class TestGetSecRegistryTickers:
    """Test SEC registry ticker retrieval."""

    def test_get_sec_registry_tickers_success(self, mock_diagnose_tickers):
        """Test successful SEC registry ticker retrieval."""
        mock_tickers_data = {
            "0": {"ticker": "AAPL", "cik_str": 123},
            "1": {"ticker": "MSFT", "cik_str": 456},
            "2": {"ticker": "GOOGL", "cik_str": 789},
        }
        mock_diagnose_tickers.get_tickers.return_value = mock_tickers_data

        result = get_sec_registry_tickers()

        assert result["count"] == 3
        assert "AAPL" in result["tickers"]
        assert "MSFT" in result["tickers"]
        assert "GOOGL" in result["tickers"]

    def test_get_sec_registry_tickers_none_result(self, mock_diagnose_tickers):
        """Test SEC registry with None result."""
        mock_diagnose_tickers.get_tickers.return_value = None

        result = get_sec_registry_tickers()

        assert "error" in result
        assert "Failed to retrieve tickers" in result["error"]

    def test_get_sec_registry_tickers_error(self, mock_diagnose_tickers):
        """Test SEC registry with exception."""
        mock_diagnose_tickers.get_tickers.side_effect = Exception("Network error")

        result = get_sec_registry_tickers()

        assert "error" in result
        assert "Network error" in result["error"]


class TestCheckDataFormatIssue:
    """Test data format issue checking."""

    def test_check_data_format_issue_no_issues(self, mock_queue_broker):
        """Test format check with valid data."""
        mock_queue_broker.peek_queue.return_value = ["item1"]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "candles": [{"datetime": 1609459200000, "open": 100.0, "close": 104.0}],
        }

        result = check_data_format_issue(mock_queue_broker)

        assert result["issues_found"] == 0
        assert result["issues"] == []

    def test_check_data_format_issue_missing_candles(self, mock_queue_broker):
        """Test format check with missing candles key."""
        mock_queue_broker.peek_queue.return_value = ["item1"]
        mock_queue_broker.get_data.return_value = {"ticker": "AAPL"}

        result = check_data_format_issue(mock_queue_broker)

        assert result["issues_found"] == 1
        assert "No 'candles' key" in result["issues"][0]

    def test_check_data_format_issue_candles_not_list(self, mock_queue_broker):
        """Test format check with candles not being a list."""
        mock_queue_broker.peek_queue.return_value = ["item1"]
        mock_queue_broker.get_data.return_value = {"ticker": "AAPL", "candles": "not_a_list"}

        result = check_data_format_issue(mock_queue_broker)

        assert result["issues_found"] == 1
        assert "not a list" in result["issues"][0]

    def test_check_data_format_issue_empty_candles(self, mock_queue_broker):
        """Test format check with empty candles list."""
        mock_queue_broker.peek_queue.return_value = ["item1"]
        mock_queue_broker.get_data.return_value = {"ticker": "AAPL", "candles": []}

        result = check_data_format_issue(mock_queue_broker)

        assert result["issues_found"] == 1
        assert "empty" in result["issues"][0]

    def test_check_data_format_issue_missing_datetime(self, mock_queue_broker):
        """Test format check with missing datetime key."""
        mock_queue_broker.peek_queue.return_value = ["item1"]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "candles": [{"open": 100.0, "close": 104.0}],
        }

        result = check_data_format_issue(mock_queue_broker)

        assert result["issues_found"] == 1
        assert "missing 'datetime' key" in result["issues"][0]


class TestMain:
    """Test main diagnostic function."""

    def test_main_executes_all_checks(
        self,
        mock_queue_broker,
        mock_influx_dependencies,
        mock_diagnose_bad_ticker_client,
        mock_diagnose_tickers,
        mock_diagnose_sp500_tickers,
    ):
        """Test main function executes all diagnostic checks."""
        mock_queue_broker.get_queue_size.return_value = 0
        mock_queue_broker.peek_queue.return_value = []

        mock_df = pd.DataFrame({"ticker": ["AAPL"]})
        mock_influx_dependencies["client"].query.return_value = mock_df

        mock_diagnose_bad_ticker_client.get_bad_tickers.return_value = []
        mock_diagnose_tickers.get_tickers.return_value = {"0": {"ticker": "AAPL"}}
        mock_diagnose_sp500_tickers.return_value = ["AAPL", "MSFT"]

        with (
            patch(
                "system.algo_trader.influx.diagnose_missing_data.QueueBroker"
            ) as mock_queue_class,
            patch(
                "system.algo_trader.influx.diagnose_missing_data.MarketDataInflux"
            ) as mock_influx_class,
            patch("system.algo_trader.influx.diagnose_missing_data.check_bad_tickers") as mock_bad,
            patch(
                "system.algo_trader.influx.diagnose_missing_data.get_sec_registry_tickers"
            ) as mock_sec,
            patch("builtins.print") as mock_print,
        ):
            mock_queue_class.return_value = mock_queue_broker
            mock_influx_instance = MagicMock()
            mock_influx_instance.query.return_value = mock_df
            mock_influx_class.return_value = mock_influx_instance
            mock_bad.return_value = {"count": 0, "tickers": []}
            mock_sec.return_value = {"count": 2, "tickers": ["AAPL", "MSFT"]}

            result = main()

            assert result == 0
            assert mock_print.called
