"""Unit tests for BaseMySQLClient - MySQL Database Operations.

Tests cover client initialization, connection management, CRUD operations,
transaction handling, and error handling.
All MySQL operations are mocked to avoid requiring a database connection.
"""

import os
from unittest.mock import ANY, MagicMock, patch

import pytest

from infrastructure.config import MySQLConfig
from infrastructure.mysql.mysql import BaseMySQLClient


class ConcreteMySQLClient(BaseMySQLClient):
    """Concrete implementation for testing abstract BaseMySQLClient."""

    pass


class TestMySQLClientInitialization:
    """Test BaseMySQLClient initialization and configuration."""

    @pytest.fixture
    def mock_pymysql(self):
        """Fixture to mock pymysql module."""
        with patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql_module:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value = mock_cursor
            mock_pymysql_module.connect.return_value = mock_connection

            yield {
                "module": mock_pymysql_module,
                "connection": mock_connection,
                "cursor": mock_cursor,
            }

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.mysql.mysql.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    @pytest.fixture
    def mock_config(self):
        """Fixture to mock MySQLConfig."""
        with patch("infrastructure.config.MySQLConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.host = "localhost"
            mock_config.port = 3306
            mock_config.user = "root"
            mock_config.password = ""
            mock_config.database = ""
            mock_config.charset = "utf8mb4"
            mock_config.connect_timeout = 10
            mock_config.autocommit = False
            mock_config_class.return_value = mock_config
            yield mock_config

    def test_initialization_default_config(self, mock_pymysql, mock_logger, mock_config):
        """Test initialization with default configuration."""
        client = ConcreteMySQLClient()

        assert client.host == "localhost"
        assert client.port == 3306
        assert client.user == "root"
        assert client.password == ""
        assert client.database == ""
        assert client.charset == "utf8mb4"
        assert client.connect_timeout == 10
        assert client.autocommit is False
        assert client._connection is None
        assert client._in_transaction is False

    def test_initialization_custom_config(self, mock_pymysql, mock_logger):
        """Test initialization with custom configuration."""
        custom_config = MySQLConfig(
            host="db.example.com",
            port=3307,
            user="testuser",
            password="testpass",
            database="testdb",
            charset="latin1",
            connect_timeout=20,
            autocommit=True,
        )
        client = ConcreteMySQLClient(config=custom_config)

        assert client.host == "db.example.com"
        assert client.port == 3307
        assert client.user == "testuser"
        assert client.password == "testpass"
        assert client.database == "testdb"
        assert client.charset == "latin1"
        assert client.connect_timeout == 20
        assert client.autocommit is True

    def test_initialization_from_env_vars(self, mock_pymysql, mock_logger):
        """Test initialization reads from environment variables."""
        with patch.dict(
            os.environ,
            {
                "MYSQL_HOST": "envhost",
                "MYSQL_PORT": "3308",
                "MYSQL_USER": "envuser",
                "MYSQL_PASSWORD": "envpass",
                "MYSQL_DATABASE": "envdb",
                "MYSQL_CHARSET": "utf8",
                "MYSQL_CONNECT_TIMEOUT": "15",
                "MYSQL_AUTOCOMMIT": "true",
            },
        ):
            config = MySQLConfig()
            client = ConcreteMySQLClient(config=config)

            assert client.host == "envhost"
            assert client.port == 3308
            assert client.user == "envuser"
            assert client.password == "envpass"
            assert client.database == "envdb"
            assert client.charset == "utf8"
            assert client.connect_timeout == 15
            assert client.autocommit is True

    def test_get_connection_creates_connection(self, mock_pymysql, mock_logger, mock_config):
        """Test _get_connection creates connection on first call."""
        client = ConcreteMySQLClient()
        conn = client._get_connection()

        mock_pymysql["module"].connect.assert_called_once_with(
            host="localhost",
            port=3306,
            user="root",
            password="",
            database="",
            charset="utf8mb4",
            connect_timeout=10,
            autocommit=False,
            cursorclass=ANY,  # Use ANY since the real class is used in the code
        )
        assert conn == mock_pymysql["connection"]
        assert client._connection == mock_pymysql["connection"]

    def test_get_connection_reuses_connection(self, mock_pymysql, mock_logger, mock_config):
        """Test _get_connection reuses existing connection."""
        client = ConcreteMySQLClient()
        conn1 = client._get_connection()
        conn2 = client._get_connection()

        assert conn1 == conn2
        mock_pymysql["module"].connect.assert_called_once()


class TestMySQLClientPing:
    """Test ping operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql,
            patch("infrastructure.mysql.mysql.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_pymysql.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "pymysql": mock_pymysql,
                "connection": mock_connection,
                "logger": mock_logger_instance,
            }

    def test_ping_success(self, mock_dependencies):
        """Test successful ping operation."""
        client = ConcreteMySQLClient()
        result = client.ping()

        assert result is True
        mock_dependencies["connection"].ping.assert_called_once_with(reconnect=False)
        mock_dependencies["logger"].debug.assert_called()

    def test_ping_failure(self, mock_dependencies):
        """Test ping handles connection errors."""
        mock_dependencies["connection"].ping.side_effect = Exception("Connection error")
        client = ConcreteMySQLClient()
        result = client.ping()

        assert result is False
        mock_dependencies["logger"].debug.assert_called()


class TestMySQLClientExecute:
    """Test execute operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql,
            patch("infrastructure.mysql.mysql.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.return_value = 1
            mock_cursor.__enter__.return_value = mock_cursor
            mock_connection.cursor.return_value = mock_cursor
            # Mock get_autocommit to return False so commit is called
            mock_connection.get_autocommit.return_value = False
            mock_pymysql.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "pymysql": mock_pymysql,
                "connection": mock_connection,
                "cursor": mock_cursor,
                "logger": mock_logger_instance,
            }

    def test_execute_success(self, mock_dependencies):
        """Test successful execute operation."""
        client = ConcreteMySQLClient()
        result = client.execute("INSERT INTO test VALUES (%s)", ("value",))

        assert result == 1
        mock_dependencies["cursor"].execute.assert_called_once_with(
            "INSERT INTO test VALUES (%s)", ("value",)
        )
        mock_dependencies["connection"].commit.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()

    def test_execute_without_params(self, mock_dependencies):
        """Test execute operation without parameters."""
        client = ConcreteMySQLClient()
        result = client.execute("CREATE TABLE test (id INT)")

        assert result == 1
        mock_dependencies["cursor"].execute.assert_called_once_with(
            "CREATE TABLE test (id INT)", ()
        )
        mock_dependencies["connection"].commit.assert_called_once()

    def test_execute_failure(self, mock_dependencies):
        """Test execute handles errors and rolls back if in transaction."""
        mock_dependencies["cursor"].execute.side_effect = Exception("SQL error")
        client = ConcreteMySQLClient()
        client._in_transaction = True

        with pytest.raises(Exception, match="SQL error"):
            client.execute("INSERT INTO test VALUES (%s)", ("value",))

        mock_dependencies["logger"].error.assert_called()
        assert client._in_transaction is False


class TestMySQLClientExecuteMany:
    """Test execute_many operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql,
            patch("infrastructure.mysql.mysql.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.executemany.return_value = 3
            mock_cursor.__enter__.return_value = mock_cursor
            mock_connection.cursor.return_value = mock_cursor
            # Mock get_autocommit to return False so commit is called
            mock_connection.get_autocommit.return_value = False
            mock_pymysql.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "pymysql": mock_pymysql,
                "connection": mock_connection,
                "cursor": mock_cursor,
                "logger": mock_logger_instance,
            }

    def test_execute_many_success(self, mock_dependencies):
        """Test successful execute_many operation."""
        client = ConcreteMySQLClient()
        params_list = [("value1",), ("value2",), ("value3",)]
        result = client.execute_many("INSERT INTO test VALUES (%s)", params_list)

        assert result == 3
        mock_dependencies["cursor"].executemany.assert_called_once_with(
            "INSERT INTO test VALUES (%s)", params_list
        )
        mock_dependencies["connection"].commit.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()

    def test_execute_many_failure(self, mock_dependencies):
        """Test execute_many handles errors and rolls back if in transaction."""
        mock_dependencies["cursor"].executemany.side_effect = Exception("SQL error")
        client = ConcreteMySQLClient()
        client._in_transaction = True

        with pytest.raises(Exception, match="SQL error"):
            client.execute_many("INSERT INTO test VALUES (%s)", [("value",)])

        mock_dependencies["logger"].error.assert_called()
        assert client._in_transaction is False


class TestMySQLClientFetch:
    """Test fetch operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql,
            patch("infrastructure.mysql.mysql.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value = mock_cursor
            mock_cursor.__enter__.return_value = mock_cursor
            mock_pymysql.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "pymysql": mock_pymysql,
                "connection": mock_connection,
                "cursor": mock_cursor,
                "logger": mock_logger_instance,
            }

    def test_fetchone_success(self, mock_dependencies):
        """Test successful fetchone operation."""
        mock_row = {"id": 1, "name": "test"}
        mock_dependencies["cursor"].fetchone.return_value = mock_row

        client = ConcreteMySQLClient()
        result = client.fetchone("SELECT * FROM test WHERE id = %s", (1,))

        assert result == {"id": 1, "name": "test"}
        mock_dependencies["cursor"].execute.assert_called_once_with(
            "SELECT * FROM test WHERE id = %s", (1,)
        )
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchone_no_results(self, mock_dependencies):
        """Test fetchone returns None when no results."""
        mock_dependencies["cursor"].fetchone.return_value = None

        client = ConcreteMySQLClient()
        result = client.fetchone("SELECT * FROM test WHERE id = %s", (999,))

        assert result is None
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchone_failure(self, mock_dependencies):
        """Test fetchone handles errors."""
        mock_dependencies["cursor"].execute.side_effect = Exception("SQL error")

        client = ConcreteMySQLClient()
        with pytest.raises(Exception, match="SQL error"):
            client.fetchone("SELECT * FROM test")

        mock_dependencies["logger"].error.assert_called()

    def test_fetchall_success(self, mock_dependencies):
        """Test successful fetchall operation."""
        mock_rows = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        mock_dependencies["cursor"].fetchall.return_value = mock_rows

        client = ConcreteMySQLClient()
        result = client.fetchall("SELECT * FROM test")

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "test1"}
        assert result[1] == {"id": 2, "name": "test2"}
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchall_empty_results(self, mock_dependencies):
        """Test fetchall returns empty list when no results."""
        mock_dependencies["cursor"].fetchall.return_value = []

        client = ConcreteMySQLClient()
        result = client.fetchall("SELECT * FROM test WHERE id = 999")

        assert result == []
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchmany_success(self, mock_dependencies):
        """Test successful fetchmany operation."""
        mock_row = [{"id": 1, "name": "test1"}]
        mock_dependencies["cursor"].fetchmany.return_value = mock_row

        client = ConcreteMySQLClient()
        result = client.fetchmany("SELECT * FROM test", size=5)

        assert len(result) == 1
        assert result[0] == {"id": 1, "name": "test1"}
        mock_dependencies["cursor"].fetchmany.assert_called_once_with(5)
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchmany_default_size(self, mock_dependencies):
        """Test fetchmany uses default size of 1."""
        mock_dependencies["cursor"].fetchmany.return_value = []

        client = ConcreteMySQLClient()
        client.fetchmany("SELECT * FROM test")

        mock_dependencies["cursor"].fetchmany.assert_called_once_with(1)


class TestMySQLClientTransactions:
    """Test transaction operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql,
            patch("infrastructure.mysql.mysql.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_pymysql.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "pymysql": mock_pymysql,
                "connection": mock_connection,
                "logger": mock_logger_instance,
            }

    def test_begin_success(self, mock_dependencies):
        """Test successful begin transaction."""
        client = ConcreteMySQLClient()
        client.begin()

        assert client._in_transaction is True
        mock_dependencies["connection"].autocommit.assert_called_once_with(False)
        mock_dependencies["logger"].debug.assert_called()

    def test_begin_already_in_transaction(self, mock_dependencies):
        """Test begin warns when already in transaction."""
        client = ConcreteMySQLClient()
        client._in_transaction = True
        client.begin()

        mock_dependencies["logger"].warning.assert_called()
        mock_dependencies["connection"].autocommit.assert_not_called()

    def test_commit_success(self, mock_dependencies):
        """Test successful commit transaction."""
        client = ConcreteMySQLClient()
        client._in_transaction = True
        client.commit()

        assert client._in_transaction is False
        mock_dependencies["connection"].commit.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()

    def test_commit_not_in_transaction(self, mock_dependencies):
        """Test commit warns when not in transaction."""
        client = ConcreteMySQLClient()
        client._in_transaction = False
        client.commit()

        mock_dependencies["logger"].warning.assert_called()
        mock_dependencies["connection"].commit.assert_not_called()

    def test_rollback_success(self, mock_dependencies):
        """Test successful rollback transaction."""
        client = ConcreteMySQLClient()
        client._in_transaction = True
        client.rollback()

        assert client._in_transaction is False
        mock_dependencies["connection"].rollback.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()


class TestMySQLClientConnectionManagement:
    """Test connection management operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql,
            patch("infrastructure.mysql.mysql.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_pymysql.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "pymysql": mock_pymysql,
                "connection": mock_connection,
                "logger": mock_logger_instance,
            }

    def test_close_success(self, mock_dependencies):
        """Test successful close operation."""
        client = ConcreteMySQLClient()
        client._connection = mock_dependencies["connection"]
        client._in_transaction = False
        client.close()

        mock_dependencies["connection"].close.assert_called_once()
        assert client._connection is None
        mock_dependencies["logger"].info.assert_called()

    def test_close_with_active_transaction(self, mock_dependencies):
        """Test close rolls back active transaction."""
        client = ConcreteMySQLClient()
        client._connection = mock_dependencies["connection"]
        client._in_transaction = True

        with patch.object(client, "rollback") as mock_rollback:
            client.close()

            mock_rollback.assert_called_once()
            mock_dependencies["connection"].close.assert_called_once()
            assert client._connection is None

    def test_context_manager_success(self, mock_dependencies):
        """Test context manager usage."""
        client = ConcreteMySQLClient()
        client._connection = mock_dependencies["connection"]

        with client:
            assert client._connection is not None

        mock_dependencies["connection"].close.assert_called_once()

    def test_context_manager_with_exception(self, mock_dependencies):
        """Test context manager rolls back on exception."""
        client = ConcreteMySQLClient()
        client._connection = mock_dependencies["connection"]
        client._in_transaction = True

        with patch.object(client, "rollback") as mock_rollback:
            try:
                with client:
                    raise ValueError("Test error")
            except ValueError:
                pass

            assert mock_rollback.call_count >= 1
            mock_dependencies["connection"].close.assert_called_once()
