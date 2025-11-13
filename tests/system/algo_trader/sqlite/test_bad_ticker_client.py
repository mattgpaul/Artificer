"""Unit tests for BadTickerClient - Bad Ticker Tracking.

Tests cover initialization, table creation, logging, querying, and removal
of bad tickers. All SQLite operations are mocked to avoid requiring a database.
"""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.config import SQLiteConfig
from system.algo_trader.sqlite.bad_ticker_client import BadTickerClient


class TestBadTickerClientInitialization:
    """Test BadTickerClient initialization and configuration."""

    def test_initialization_default_config(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test initialization with default configuration."""
        client = BadTickerClient()

        assert client.db_path == "./data/algo_trader.db"
        mock_logger.info.assert_called()

    def test_initialization_with_env_var(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test initialization reads SQLITE_DB_PATH from environment."""
        with patch(
            "system.algo_trader.sqlite.bad_ticker_client.os.getenv",
            return_value="/custom/path/db.db",
        ):
            mock_sqlite_config.db_path = "/custom/path/db.db"
            client = BadTickerClient()

            assert client.db_path == "/custom/path/db.db"

    def test_initialization_with_custom_config(self, mock_sqlite, mock_logger):
        """Test initialization with custom SQLiteConfig."""
        custom_config = SQLiteConfig(db_path="/tmp/test.db")
        client = BadTickerClient(config=custom_config)

        assert client.db_path == "/tmp/test.db"

    def test_initialization_creates_table(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test initialization automatically creates table."""
        _ = BadTickerClient()  # Trigger initialization which calls create_table

        # Verify create_table was called
        assert mock_sqlite["connection"].execute.call_count >= 1
        create_table_call = [
            call
            for call in mock_sqlite["connection"].execute.call_args_list
            if "CREATE TABLE" in str(call)
        ]
        assert len(create_table_call) > 0


class TestBadTickerClientTableCreation:
    """Test bad_tickers table creation."""

    def test_create_table_success(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test successful table creation."""
        client = BadTickerClient()
        client.create_table()

        # Verify CREATE TABLE query was executed
        calls = mock_sqlite["connection"].execute.call_args_list
        create_table_calls = [call for call in calls if "CREATE TABLE" in str(call[0])]
        assert len(create_table_calls) > 0
        mock_logger.info.assert_called()

    def test_create_table_failure(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test table creation handles errors."""
        client = BadTickerClient()
        # Set side_effect after initialization to avoid affecting create_table() in __init__
        mock_sqlite["connection"].execute.side_effect = RuntimeError("Database error")

        with pytest.raises(RuntimeError, match="Database error"):
            client.create_table()

        mock_logger.error.assert_called()


class TestBadTickerClientOperations:
    """Test bad ticker CRUD operations."""

    def test_log_bad_ticker_success(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test logging bad ticker successfully."""
        mock_sqlite["cursor"].rowcount = 1

        client = BadTickerClient()
        result = client.log_bad_ticker("AAPL", "2024-01-01T00:00:00", "Invalid symbol")

        assert result is True
        mock_logger.debug.assert_called()

    def test_log_bad_ticker_failure(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test logging bad ticker handles errors."""
        client = BadTickerClient()
        mock_sqlite["connection"].execute.side_effect = Exception("DB error")

        result = client.log_bad_ticker("AAPL", "2024-01-01T00:00:00", "Invalid symbol")

        assert result is False
        mock_logger.error.assert_called()

    def test_get_bad_tickers_success(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test retrieving bad tickers successfully."""
        mock_row1 = MagicMock()
        mock_row1.keys.return_value = ["ticker", "timestamp", "reason"]
        mock_row1.__getitem__.side_effect = lambda key: {
            "ticker": "AAPL",
            "timestamp": "2024-01-01T00:00:00",
            "reason": "Invalid",
        }[key]

        mock_row2 = MagicMock()
        mock_row2.keys.return_value = ["ticker", "timestamp", "reason"]
        mock_row2.__getitem__.side_effect = lambda key: {
            "ticker": "TSLA",
            "timestamp": "2024-01-02T00:00:00",
            "reason": "Error",
        }[key]

        mock_sqlite["cursor"].fetchall.return_value = [mock_row1, mock_row2]

        client = BadTickerClient()
        results = client.get_bad_tickers(limit=10)

        assert len(results) == 2
        assert results[0]["ticker"] == "AAPL"
        assert results[1]["ticker"] == "TSLA"

    def test_get_bad_tickers_failure(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test get_bad_tickers handles errors."""
        client = BadTickerClient()
        mock_sqlite["connection"].execute.side_effect = Exception("DB error")

        results = client.get_bad_tickers()

        assert results == []
        mock_logger.error.assert_called()

    @pytest.mark.parametrize("found,expected", [(True, True), (False, False)])
    def test_is_bad_ticker(self, mock_sqlite, mock_logger, mock_sqlite_config, found, expected):
        """Test checking if ticker is bad (found and not found)."""
        client = BadTickerClient()
        if found:
            mock_row = MagicMock()
            mock_row.keys.return_value = ["1"]
            mock_sqlite["cursor"].fetchone.return_value = mock_row
        else:
            mock_sqlite["cursor"].fetchone.return_value = None

        result = client.is_bad_ticker("AAPL")

        assert result == expected

    def test_is_bad_ticker_error(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test is_bad_ticker handles errors."""
        client = BadTickerClient()
        mock_sqlite["connection"].execute.side_effect = Exception("DB error")

        result = client.is_bad_ticker("AAPL")

        assert result is False
        mock_logger.error.assert_called()

    def test_remove_bad_ticker_success(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test removing bad ticker successfully."""
        mock_sqlite["cursor"].rowcount = 1

        client = BadTickerClient()
        result = client.remove_bad_ticker("AAPL")

        assert result is True
        mock_logger.debug.assert_called()

    def test_remove_bad_ticker_failure(self, mock_sqlite, mock_logger, mock_sqlite_config):
        """Test removing bad ticker handles errors."""
        client = BadTickerClient()
        mock_sqlite["connection"].execute.side_effect = Exception("DB error")

        result = client.remove_bad_ticker("AAPL")

        assert result is False
        mock_logger.error.assert_called()
