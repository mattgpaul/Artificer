"""Unit tests for BadTickerClient - Bad Ticker Tracking.

Tests cover initialization, table creation, logging, querying, and removal
of bad tickers. All MySQL operations are mocked to avoid requiring a database.
"""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.config import MySQLConfig
from system.algo_trader.mysql.bad_ticker_client import BadTickerClient


class TestBadTickerClientInitialization:
    """Test BadTickerClient initialization and configuration."""

    def test_initialization_default_config(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test initialization with default configuration."""
        client = BadTickerClient()

        assert client.host == "localhost"
        assert client.database == "algo_trader"
        mock_logger.info.assert_called()

    def test_initialization_with_env_var(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test initialization reads MYSQL_* from environment."""
        with (
            patch("system.algo_trader.mysql.bad_ticker_client.os.getenv") as mock_getenv,
        ):
            mock_getenv.side_effect = lambda key, default=None: {
                "MYSQL_HOST": "custom-host",
                "MYSQL_PORT": "3307",
                "MYSQL_USER": "custom-user",
                "MYSQL_PASSWORD": "custom-password",
                "MYSQL_DATABASE": "custom-db",
            }.get(key, default)

            client = BadTickerClient()

            assert client.host == "custom-host"
            assert client.port == 3307
            assert client.user == "custom-user"
            assert client.password == "custom-password"
            assert client.database == "custom-db"

    def test_initialization_with_custom_config(self, mock_mysql, mock_logger):
        """Test initialization with custom MySQLConfig."""
        custom_config = MySQLConfig(
            host="custom-host",
            port=3307,
            user="custom-user",
            password="custom-password",
            database="custom-db",
        )
        client = BadTickerClient(config=custom_config)

        assert client.host == "custom-host"
        assert client.database == "custom-db"

    def test_initialization_creates_table(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test initialization automatically creates table."""
        _ = BadTickerClient()  # Trigger initialization which calls create_table

        # Verify create_table was called
        assert mock_mysql["cursor"].execute.call_count >= 1
        create_table_calls = [
            call
            for call in mock_mysql["cursor"].execute.call_args_list
            if "CREATE TABLE" in str(call)
        ]
        assert len(create_table_calls) > 0


class TestBadTickerClientTableCreation:
    """Test bad_tickers table creation."""

    def test_create_table_success(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test successful table creation."""
        client = BadTickerClient()
        client.create_table()

        # Verify CREATE TABLE query was executed
        calls = mock_mysql["cursor"].execute.call_args_list
        create_table_calls = [call for call in calls if "CREATE TABLE" in str(call[0])]
        assert len(create_table_calls) > 0
        mock_logger.info.assert_called()

    def test_create_table_failure(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test table creation handles errors."""
        client = BadTickerClient()
        # Set side_effect after initialization to avoid affecting create_table() in __init__
        mock_mysql["cursor"].execute.side_effect = RuntimeError("Database error")

        with pytest.raises(RuntimeError, match="Database error"):
            client.create_table()

        mock_logger.error.assert_called()


class TestBadTickerClientOperations:
    """Test bad ticker CRUD operations."""

    def test_log_bad_ticker_success(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test logging bad ticker successfully."""
        mock_mysql["cursor"].execute.return_value = 1

        client = BadTickerClient()
        result = client.log_bad_ticker("AAPL", "2024-01-01T00:00:00", "Invalid symbol")

        assert result is True
        mock_logger.debug.assert_called()

    def test_log_bad_ticker_failure(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test logging bad ticker handles errors."""
        client = BadTickerClient()
        mock_mysql["cursor"].execute.side_effect = Exception("DB error")

        result = client.log_bad_ticker("AAPL", "2024-01-01T00:00:00", "Invalid symbol")

        assert result is False
        mock_logger.error.assert_called()

    def test_get_bad_tickers_success(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test retrieving bad tickers successfully."""
        mock_row1 = {"ticker": "AAPL", "timestamp": "2024-01-01T00:00:00", "reason": "Invalid"}
        mock_row2 = {"ticker": "TSLA", "timestamp": "2024-01-02T00:00:00", "reason": "Error"}

        mock_mysql["cursor"].fetchall.return_value = [mock_row1, mock_row2]

        client = BadTickerClient()
        results = client.get_bad_tickers(limit=10)

        assert len(results) == 2
        assert results[0]["ticker"] == "AAPL"
        assert results[1]["ticker"] == "TSLA"

    def test_get_bad_tickers_failure(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test get_bad_tickers handles errors."""
        client = BadTickerClient()
        mock_mysql["cursor"].execute.side_effect = Exception("DB error")

        results = client.get_bad_tickers()

        assert results == []
        mock_logger.error.assert_called()

    @pytest.mark.parametrize("found,expected", [(True, True), (False, False)])
    def test_is_bad_ticker(self, mock_mysql, mock_logger, mock_mysql_config, found, expected):
        """Test checking if ticker is bad (found and not found)."""
        client = BadTickerClient()
        if found:
            mock_mysql["cursor"].fetchone.return_value = {"1": 1}
        else:
            mock_mysql["cursor"].fetchone.return_value = None

        result = client.is_bad_ticker("AAPL")

        assert result == expected

    def test_is_bad_ticker_error(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test is_bad_ticker handles errors."""
        client = BadTickerClient()
        mock_mysql["cursor"].execute.side_effect = Exception("DB error")

        result = client.is_bad_ticker("AAPL")

        assert result is False
        mock_logger.error.assert_called()

    def test_remove_bad_ticker_success(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test removing bad ticker successfully."""
        mock_mysql["cursor"].execute.return_value = 1

        client = BadTickerClient()
        result = client.remove_bad_ticker("AAPL")

        assert result is True
        mock_logger.debug.assert_called()

    def test_remove_bad_ticker_failure(self, mock_mysql, mock_logger, mock_mysql_config):
        """Test removing bad ticker handles errors."""
        client = BadTickerClient()
        mock_mysql["cursor"].execute.side_effect = Exception("DB error")

        result = client.remove_bad_ticker("AAPL")

        assert result is False
        mock_logger.error.assert_called()

