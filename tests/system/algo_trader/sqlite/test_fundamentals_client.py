"""Unit tests for FundamentalsClient - Fundamentals Data Storage.

Tests cover initialization, table creation, and upsert operations.
All SQLite operations are mocked to avoid requiring a database.
"""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.config import SQLiteConfig
from system.algo_trader.sqlite.fundamentals_client import FundamentalsClient


class TestFundamentalsClientInitialization:
    """Test FundamentalsClient initialization and configuration."""

    def test_initialization_default_config(self, mock_sqlite, mock_logger, mock_fundamentals_os):
        """Test initialization with default configuration."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = "./data/algo_trader.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()

            assert client.db_path == "./data/algo_trader.db"
            mock_logger.info.assert_called()

    def test_initialization_with_env_var(self, mock_sqlite, mock_logger, mock_fundamentals_os):
        """Test initialization reads SQLITE_DB_PATH from environment."""
        with (
            patch("infrastructure.config.SQLiteConfig") as mock_config_class,
            patch(
                "system.algo_trader.sqlite.fundamentals_client.os.getenv",
                return_value="/custom/path/db.db",
            ),
        ):
            mock_config = MagicMock()
            mock_config.db_path = "/custom/path/db.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()

            assert client.db_path == "/custom/path/db.db"

    def test_initialization_with_custom_config(
        self, mock_sqlite, mock_logger, mock_fundamentals_os
    ):
        """Test initialization with custom SQLiteConfig."""
        custom_config = SQLiteConfig(db_path="/tmp/test.db")
        client = FundamentalsClient(config=custom_config)

        assert client.db_path == "/tmp/test.db"

    def test_initialization_creates_table(self, mock_sqlite, mock_logger, mock_fundamentals_os):
        """Test initialization automatically creates table."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = "./data/algo_trader.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config

            _ = FundamentalsClient()  # Trigger initialization which calls create_table

            # Verify create_table was called
            assert mock_sqlite["connection"].execute.call_count >= 1
            create_table_call = [
                call
                for call in mock_sqlite["connection"].execute.call_args_list
                if "CREATE TABLE" in str(call)
            ]
            assert len(create_table_call) > 0


class TestFundamentalsClientTableCreation:
    """Test fundamentals table creation."""

    def test_create_table_success(self, mock_sqlite, mock_logger, mock_fundamentals_os):
        """Test successful table creation."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = "./data/algo_trader.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            client.create_table()

            # Verify CREATE TABLE query was executed
            calls = mock_sqlite["connection"].execute.call_args_list
            create_table_calls = [call for call in calls if "CREATE TABLE" in str(call)]
            assert len(create_table_calls) > 0
            mock_logger.info.assert_called()

    def test_create_table_failure(self, mock_sqlite, mock_logger, mock_fundamentals_os):
        """Test table creation handles errors."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = "./data/algo_trader.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            # Set side_effect after initialization to avoid affecting create_table() in __init__
            mock_sqlite["connection"].execute.side_effect = RuntimeError("Database error")

            with pytest.raises(RuntimeError, match="Database error"):
                client.create_table()

            mock_logger.error.assert_called()


class TestFundamentalsClientOperations:
    """Test fundamentals CRUD operations."""

    def test_upsert_fundamentals_success(self, mock_sqlite, mock_logger, mock_fundamentals_os):
        """Test upserting fundamentals successfully."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = "./data/algo_trader.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config
            mock_sqlite["cursor"].rowcount = 1

            client = FundamentalsClient()
            static_data = {
                "ticker": "AAPL",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "entity_name": "Apple Inc.",
                "sic": "3571",
            }

            result = client.upsert_fundamentals(static_data)

            assert result is True
            mock_logger.debug.assert_called()

    def test_upsert_fundamentals_with_none_values(
        self, mock_sqlite, mock_logger, mock_fundamentals_os
    ):
        """Test upserting fundamentals with None values."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = "./data/algo_trader.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            static_data = {
                "ticker": "AAPL",
                "sector": None,
                "industry": None,
                "entity_name": "Apple Inc.",
                "sic": None,
            }

            result = client.upsert_fundamentals(static_data)

            assert result is True

    def test_upsert_fundamentals_failure(self, mock_sqlite, mock_logger, mock_fundamentals_os):
        """Test upserting fundamentals handles errors."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = "./data/algo_trader.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            mock_sqlite["connection"].execute.side_effect = Exception("DB error")

            static_data = {
                "ticker": "AAPL",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "entity_name": "Apple Inc.",
                "sic": "3571",
            }

            result = client.upsert_fundamentals(static_data)

            assert result is False
            mock_logger.error.assert_called()

    def test_upsert_fundamentals_partial_data(self, mock_sqlite, mock_logger, mock_fundamentals_os):
        """Test upserting fundamentals with partial data."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = "./data/algo_trader.db"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            static_data = {
                "ticker": "AAPL",
            }

            result = client.upsert_fundamentals(static_data)

            assert result is True
