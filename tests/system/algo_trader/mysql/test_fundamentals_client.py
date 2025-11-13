"""Unit tests for FundamentalsClient - Fundamentals Data Storage.

Tests cover initialization, table creation, and upsert operations.
All MySQL operations are mocked to avoid requiring a database.
"""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.config import MySQLConfig
from system.algo_trader.mysql.fundamentals_client import FundamentalsClient


class TestFundamentalsClientInitialization:
    """Test FundamentalsClient initialization and configuration."""

    def test_initialization_default_config(self, mock_mysql, mock_logger):
        """Test initialization with default configuration."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = "algo_trader"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()

            assert client.host == "localhost"
            assert client.database == "algo_trader"
            mock_logger.info.assert_called()

    def test_initialization_with_env_var(self, mock_mysql, mock_logger):
        """Test initialization reads MYSQL_* from environment."""
        with (
            patch("infrastructure.config.MySQLConfig") as mock_config_class,
            patch("system.algo_trader.mysql.fundamentals_client.os.getenv") as mock_getenv,
        ):
            mock_config = MagicMock()
            mock_config.host = "custom-host"
            mock_config.port = 3307
            mock_config.user = "custom-user"
            mock_config.password = "custom-password"
            mock_config.database = "custom-db"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config

            mock_getenv.side_effect = lambda key, default=None: {
                "MYSQL_HOST": "custom-host",
                "MYSQL_PORT": "3307",
                "MYSQL_USER": "custom-user",
                "MYSQL_PASSWORD": "custom-password",
                "MYSQL_DATABASE": "custom-db",
            }.get(key, default)

            client = FundamentalsClient()

            assert client.host == "custom-host"
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
        client = FundamentalsClient(config=custom_config)

        assert client.host == "custom-host"
        assert client.database == "custom-db"

    def test_initialization_creates_table(self, mock_mysql, mock_logger):
        """Test initialization automatically creates table."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = "algo_trader"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config

            _ = FundamentalsClient()  # Trigger initialization which calls create_table

            # Verify create_table was called
            assert mock_mysql["cursor"].execute.call_count >= 1
            create_table_calls = [
                call
                for call in mock_mysql["cursor"].execute.call_args_list
                if "CREATE TABLE" in str(call)
            ]
            assert len(create_table_calls) > 0


class TestFundamentalsClientTableCreation:
    """Test fundamentals table creation."""

    def test_create_table_success(self, mock_mysql, mock_logger):
        """Test successful table creation."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = "algo_trader"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            client.create_table()

            # Verify CREATE TABLE query was executed
            calls = mock_mysql["cursor"].execute.call_args_list
            create_table_calls = [call for call in calls if "CREATE TABLE" in str(call)]
            assert len(create_table_calls) > 0
            mock_logger.info.assert_called()

    def test_create_table_failure(self, mock_mysql, mock_logger):
        """Test table creation handles errors."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = "algo_trader"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            # Set side_effect after initialization to avoid affecting create_table() in __init__
            mock_mysql["cursor"].execute.side_effect = RuntimeError("Database error")

            with pytest.raises(RuntimeError, match="Database error"):
                client.create_table()

            mock_logger.error.assert_called()


class TestFundamentalsClientOperations:
    """Test fundamentals CRUD operations."""

    def test_upsert_fundamentals_success(self, mock_mysql, mock_logger):
        """Test upserting fundamentals successfully."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = "algo_trader"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config
            mock_mysql["cursor"].execute.return_value = 1

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

    def test_upsert_fundamentals_with_none_values(self, mock_mysql, mock_logger):
        """Test upserting fundamentals with None values."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = "algo_trader"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
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

    def test_upsert_fundamentals_failure(self, mock_mysql, mock_logger):
        """Test upserting fundamentals handles errors."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = "algo_trader"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            mock_mysql["cursor"].execute.side_effect = Exception("DB error")

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

    def test_upsert_fundamentals_partial_data(self, mock_mysql, mock_logger):
        """Test upserting fundamentals with partial data."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = "algo_trader"
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config

            client = FundamentalsClient()
            static_data = {
                "ticker": "AAPL",
            }

            result = client.upsert_fundamentals(static_data)

            assert result is True

