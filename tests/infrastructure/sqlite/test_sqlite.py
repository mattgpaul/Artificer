"""Unit tests for BaseSQLiteClient - SQLite Database Operations.

Tests cover client initialization, connection management, CRUD operations,
transaction handling, and error handling.
All SQLite operations are mocked to avoid requiring a database file.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from infrastructure.config import SQLiteConfig
from infrastructure.sqlite.sqlite import BaseSQLiteClient


class ConcreteSQLiteClient(BaseSQLiteClient):
    """Concrete implementation for testing abstract BaseSQLiteClient."""

    pass


class TestSQLiteClientInitialization:
    """Test BaseSQLiteClient initialization and configuration."""

    @pytest.fixture
    def mock_sqlite(self):
        """Fixture to mock sqlite3 module."""
        with patch("infrastructure.sqlite.sqlite.sqlite3") as mock_sqlite_module:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connection.execute.return_value = mock_cursor
            mock_sqlite_module.connect.return_value = mock_connection

            yield {
                "module": mock_sqlite_module,
                "connection": mock_connection,
                "cursor": mock_cursor,
            }

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.sqlite.sqlite.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    @pytest.fixture
    def mock_config(self):
        """Fixture to mock SQLiteConfig."""
        with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.db_path = ":memory:"
            mock_config.timeout = 30
            mock_config.isolation_level = "DEFERRED"
            mock_config_class.return_value = mock_config
            yield mock_config

    def test_initialization_default_config(self, mock_sqlite, mock_logger, mock_config):
        """Test initialization with default configuration."""
        client = ConcreteSQLiteClient()

        assert client.db_path == ":memory:"
        assert client.timeout == 30
        assert client.isolation_level == "DEFERRED"
        assert client._connection is None
        assert client._in_transaction is False

    def test_initialization_custom_config(self, mock_sqlite, mock_logger):
        """Test initialization with custom configuration."""
        custom_config = SQLiteConfig(
            db_path="/tmp/test.db", timeout=60, isolation_level="IMMEDIATE"
        )
        client = ConcreteSQLiteClient(config=custom_config)

        assert client.db_path == "/tmp/test.db"
        assert client.timeout == 60
        assert client.isolation_level == "IMMEDIATE"

    def test_initialization_from_env_vars(self, mock_sqlite, mock_logger):
        """Test initialization reads from environment variables."""
        with patch.dict(
            os.environ,
            {
                "SQLITE_DB_PATH": "/tmp/env.db",
                "SQLITE_TIMEOUT": "45",
                "SQLITE_ISOLATION_LEVEL": "EXCLUSIVE",
            },
        ):
            config = SQLiteConfig()
            client = ConcreteSQLiteClient(config=config)

            assert client.db_path == "/tmp/env.db"
            assert client.timeout == 45
            assert client.isolation_level == "EXCLUSIVE"

    def test_get_connection_creates_connection(self, mock_sqlite, mock_logger, mock_config):
        """Test _get_connection creates connection on first call."""
        client = ConcreteSQLiteClient()
        conn = client._get_connection()

        mock_sqlite["module"].connect.assert_called_once_with(
            ":memory:", timeout=30, isolation_level="DEFERRED"
        )
        assert conn == mock_sqlite["connection"]
        assert client._connection == mock_sqlite["connection"]
        assert mock_sqlite["connection"].row_factory is not None

    def test_get_connection_reuses_connection(self, mock_sqlite, mock_logger, mock_config):
        """Test _get_connection reuses existing connection."""
        client = ConcreteSQLiteClient()
        conn1 = client._get_connection()
        conn2 = client._get_connection()

        assert conn1 == conn2
        mock_sqlite["module"].connect.assert_called_once()


class TestSQLiteClientPing:
    """Test ping operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.sqlite.sqlite.sqlite3") as mock_sqlite,
            patch("infrastructure.sqlite.sqlite.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (1,)
            mock_connection.execute.return_value = mock_cursor
            mock_sqlite.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "sqlite": mock_sqlite,
                "connection": mock_connection,
                "cursor": mock_cursor,
                "logger": mock_logger_instance,
            }

    def test_ping_success(self, mock_dependencies):
        """Test successful ping operation."""
        client = ConcreteSQLiteClient()
        result = client.ping()

        assert result is True
        mock_dependencies["connection"].execute.assert_called_once_with("SELECT 1")
        mock_dependencies["cursor"].fetchone.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()

    def test_ping_failure(self, mock_dependencies):
        """Test ping handles connection errors."""
        mock_dependencies["connection"].execute.side_effect = Exception("Connection error")
        client = ConcreteSQLiteClient()
        result = client.ping()

        assert result is False
        mock_dependencies["logger"].debug.assert_called()


class TestSQLiteClientExecute:
    """Test execute operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.sqlite.sqlite.sqlite3") as mock_sqlite,
            patch("infrastructure.sqlite.sqlite.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_connection.execute.return_value = mock_cursor
            mock_sqlite.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "sqlite": mock_sqlite,
                "connection": mock_connection,
                "cursor": mock_cursor,
                "logger": mock_logger_instance,
            }

    def test_execute_success(self, mock_dependencies):
        """Test successful execute operation."""
        client = ConcreteSQLiteClient()
        result = client.execute("INSERT INTO test VALUES (?)", ("value",))

        assert result == 1
        mock_dependencies["connection"].execute.assert_called_once_with(
            "INSERT INTO test VALUES (?)", ("value",)
        )
        mock_dependencies["connection"].commit.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()

    def test_execute_without_params(self, mock_dependencies):
        """Test execute operation without parameters."""
        client = ConcreteSQLiteClient()
        result = client.execute("CREATE TABLE test (id INTEGER)")

        assert result == 1
        mock_dependencies["connection"].execute.assert_called_once_with(
            "CREATE TABLE test (id INTEGER)", ()
        )
        mock_dependencies["connection"].commit.assert_called_once()

    def test_execute_failure(self, mock_dependencies):
        """Test execute handles errors and rolls back if in transaction."""
        mock_dependencies["connection"].execute.side_effect = Exception("SQL error")
        client = ConcreteSQLiteClient()
        client._in_transaction = True

        with pytest.raises(Exception, match="SQL error"):
            client.execute("INSERT INTO test VALUES (?)", ("value",))

        mock_dependencies["logger"].error.assert_called()
        # rollback should be called
        assert client._in_transaction is False

    def test_execute_failure_not_in_transaction(self, mock_dependencies):
        """Test execute handles errors when not in transaction."""
        mock_dependencies["connection"].execute.side_effect = Exception("SQL error")
        client = ConcreteSQLiteClient()
        client._in_transaction = False

        with pytest.raises(Exception, match="SQL error"):
            client.execute("INSERT INTO test VALUES (?)", ("value",))

        mock_dependencies["logger"].error.assert_called()


class TestSQLiteClientExecuteMany:
    """Test execute_many operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.sqlite.sqlite.sqlite3") as mock_sqlite,
            patch("infrastructure.sqlite.sqlite.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 3
            mock_connection.executemany.return_value = mock_cursor
            mock_sqlite.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "sqlite": mock_sqlite,
                "connection": mock_connection,
                "cursor": mock_cursor,
                "logger": mock_logger_instance,
            }

    def test_execute_many_success(self, mock_dependencies):
        """Test successful execute_many operation."""
        client = ConcreteSQLiteClient()
        params_list = [("value1",), ("value2",), ("value3",)]
        result = client.execute_many("INSERT INTO test VALUES (?)", params_list)

        assert result == 3
        mock_dependencies["connection"].executemany.assert_called_once_with(
            "INSERT INTO test VALUES (?)", params_list
        )
        mock_dependencies["connection"].commit.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()

    def test_execute_many_failure(self, mock_dependencies):
        """Test execute_many handles errors and rolls back if in transaction."""
        mock_dependencies["connection"].executemany.side_effect = Exception("SQL error")
        client = ConcreteSQLiteClient()
        client._in_transaction = True

        with pytest.raises(Exception, match="SQL error"):
            client.execute_many("INSERT INTO test VALUES (?)", [("value",)])

        mock_dependencies["logger"].error.assert_called()
        assert client._in_transaction is False


class TestSQLiteClientFetch:
    """Test fetch operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.sqlite.sqlite.sqlite3") as mock_sqlite,
            patch("infrastructure.sqlite.sqlite.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_connection.execute.return_value = mock_cursor
            mock_sqlite.connect.return_value = mock_connection
            mock_sqlite.Row = Mock

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "sqlite": mock_sqlite,
                "connection": mock_connection,
                "cursor": mock_cursor,
                "logger": mock_logger_instance,
            }

    def test_fetchone_success(self, mock_dependencies):
        """Test successful fetchone operation."""
        mock_row = MagicMock()
        mock_row.keys.return_value = ["id", "name"]
        mock_row.__getitem__.side_effect = lambda key: {"id": 1, "name": "test"}[key]
        mock_dependencies["cursor"].fetchone.return_value = mock_row

        client = ConcreteSQLiteClient()
        result = client.fetchone("SELECT * FROM test WHERE id = ?", (1,))

        assert result == {"id": 1, "name": "test"}
        mock_dependencies["connection"].execute.assert_called_once_with(
            "SELECT * FROM test WHERE id = ?", (1,)
        )
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchone_no_results(self, mock_dependencies):
        """Test fetchone returns None when no results."""
        mock_dependencies["cursor"].fetchone.return_value = None

        client = ConcreteSQLiteClient()
        result = client.fetchone("SELECT * FROM test WHERE id = ?", (999,))

        assert result is None
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchone_failure(self, mock_dependencies):
        """Test fetchone handles errors."""
        mock_dependencies["connection"].execute.side_effect = Exception("SQL error")

        client = ConcreteSQLiteClient()
        with pytest.raises(Exception, match="SQL error"):
            client.fetchone("SELECT * FROM test")

        mock_dependencies["logger"].error.assert_called()

    def test_fetchall_success(self, mock_dependencies):
        """Test successful fetchall operation."""
        mock_row1 = MagicMock()
        mock_row1.keys.return_value = ["id", "name"]
        mock_row1.__getitem__.side_effect = lambda key: {"id": 1, "name": "test1"}[key]

        mock_row2 = MagicMock()
        mock_row2.keys.return_value = ["id", "name"]
        mock_row2.__getitem__.side_effect = lambda key: {"id": 2, "name": "test2"}[key]

        mock_dependencies["cursor"].fetchall.return_value = [mock_row1, mock_row2]

        client = ConcreteSQLiteClient()
        result = client.fetchall("SELECT * FROM test")

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "test1"}
        assert result[1] == {"id": 2, "name": "test2"}
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchall_empty_results(self, mock_dependencies):
        """Test fetchall returns empty list when no results."""
        mock_dependencies["cursor"].fetchall.return_value = []

        client = ConcreteSQLiteClient()
        result = client.fetchall("SELECT * FROM test WHERE id = 999")

        assert result == []
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchall_failure(self, mock_dependencies):
        """Test fetchall handles errors."""
        mock_dependencies["connection"].execute.side_effect = Exception("SQL error")

        client = ConcreteSQLiteClient()
        with pytest.raises(Exception, match="SQL error"):
            client.fetchall("SELECT * FROM test")

        mock_dependencies["logger"].error.assert_called()

    def test_fetchmany_success(self, mock_dependencies):
        """Test successful fetchmany operation."""
        mock_row1 = MagicMock()
        mock_row1.keys.return_value = ["id", "name"]
        mock_row1.__getitem__.side_effect = lambda key: {"id": 1, "name": "test1"}[key]

        mock_dependencies["cursor"].fetchmany.return_value = [mock_row1]

        client = ConcreteSQLiteClient()
        result = client.fetchmany("SELECT * FROM test", size=5)

        assert len(result) == 1
        assert result[0] == {"id": 1, "name": "test1"}
        mock_dependencies["cursor"].fetchmany.assert_called_once_with(5)
        mock_dependencies["logger"].debug.assert_called()

    def test_fetchmany_default_size(self, mock_dependencies):
        """Test fetchmany uses default size of 1."""
        mock_dependencies["cursor"].fetchmany.return_value = []

        client = ConcreteSQLiteClient()
        client.fetchmany("SELECT * FROM test")

        mock_dependencies["cursor"].fetchmany.assert_called_once_with(1)

    def test_fetchmany_failure(self, mock_dependencies):
        """Test fetchmany handles errors."""
        mock_dependencies["connection"].execute.side_effect = Exception("SQL error")

        client = ConcreteSQLiteClient()
        with pytest.raises(Exception, match="SQL error"):
            client.fetchmany("SELECT * FROM test")

        mock_dependencies["logger"].error.assert_called()


class TestSQLiteClientTransactions:
    """Test transaction operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.sqlite.sqlite.sqlite3") as mock_sqlite,
            patch("infrastructure.sqlite.sqlite.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_cursor = MagicMock()
            mock_connection.execute.return_value = mock_cursor
            mock_sqlite.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "sqlite": mock_sqlite,
                "connection": mock_connection,
                "cursor": mock_cursor,
                "logger": mock_logger_instance,
            }

    def test_begin_success(self, mock_dependencies):
        """Test successful begin transaction."""
        client = ConcreteSQLiteClient()
        client.begin()

        assert client._in_transaction is True
        mock_dependencies["connection"].execute.assert_called_once_with("BEGIN")
        mock_dependencies["logger"].debug.assert_called()

    def test_begin_already_in_transaction(self, mock_dependencies):
        """Test begin warns when already in transaction."""
        client = ConcreteSQLiteClient()
        client._in_transaction = True
        client.begin()

        mock_dependencies["logger"].warning.assert_called()
        mock_dependencies["connection"].execute.assert_not_called()

    def test_begin_failure(self, mock_dependencies):
        """Test begin handles errors."""
        mock_dependencies["connection"].execute.side_effect = Exception("SQL error")

        client = ConcreteSQLiteClient()
        with pytest.raises(Exception, match="SQL error"):
            client.begin()

        mock_dependencies["logger"].error.assert_called()

    def test_commit_success(self, mock_dependencies):
        """Test successful commit transaction."""
        client = ConcreteSQLiteClient()
        client._in_transaction = True
        client.commit()

        assert client._in_transaction is False
        mock_dependencies["connection"].commit.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()

    def test_commit_not_in_transaction(self, mock_dependencies):
        """Test commit warns when not in transaction."""
        client = ConcreteSQLiteClient()
        client._in_transaction = False
        client.commit()

        mock_dependencies["logger"].warning.assert_called()
        mock_dependencies["connection"].commit.assert_not_called()

    def test_commit_failure(self, mock_dependencies):
        """Test commit handles errors and resets transaction state."""
        mock_dependencies["connection"].commit.side_effect = Exception("SQL error")

        client = ConcreteSQLiteClient()
        client._in_transaction = True
        with pytest.raises(Exception, match="SQL error"):
            client.commit()

        assert client._in_transaction is False
        mock_dependencies["logger"].error.assert_called()

    def test_rollback_success(self, mock_dependencies):
        """Test successful rollback transaction."""
        client = ConcreteSQLiteClient()
        client._in_transaction = True
        client.rollback()

        assert client._in_transaction is False
        mock_dependencies["connection"].rollback.assert_called_once()
        mock_dependencies["logger"].debug.assert_called()

    def test_rollback_not_in_transaction(self, mock_dependencies):
        """Test rollback warns when not in transaction."""
        client = ConcreteSQLiteClient()
        client._in_transaction = False
        client.rollback()

        mock_dependencies["logger"].warning.assert_called()
        mock_dependencies["connection"].rollback.assert_not_called()

    def test_rollback_failure(self, mock_dependencies):
        """Test rollback handles errors and resets transaction state."""
        mock_dependencies["connection"].rollback.side_effect = Exception("SQL error")

        client = ConcreteSQLiteClient()
        client._in_transaction = True
        with pytest.raises(Exception, match="SQL error"):
            client.rollback()

        assert client._in_transaction is False
        mock_dependencies["logger"].error.assert_called()


class TestSQLiteClientConnectionManagement:
    """Test connection management operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all dependencies."""
        with (
            patch("infrastructure.sqlite.sqlite.sqlite3") as mock_sqlite,
            patch("infrastructure.sqlite.sqlite.get_logger") as mock_get_logger,
        ):
            mock_connection = MagicMock()
            mock_sqlite.connect.return_value = mock_connection

            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance

            yield {
                "sqlite": mock_sqlite,
                "connection": mock_connection,
                "logger": mock_logger_instance,
            }

    def test_close_success(self, mock_dependencies):
        """Test successful close operation."""
        client = ConcreteSQLiteClient()
        client._connection = mock_dependencies["connection"]
        client._in_transaction = False
        client.close()

        mock_dependencies["connection"].close.assert_called_once()
        assert client._connection is None
        mock_dependencies["logger"].info.assert_called()

    def test_close_with_active_transaction(self, mock_dependencies):
        """Test close rolls back active transaction."""
        client = ConcreteSQLiteClient()
        client._connection = mock_dependencies["connection"]
        client._in_transaction = True

        with patch.object(client, "rollback") as mock_rollback:
            client.close()

            mock_rollback.assert_called_once()
            mock_dependencies["connection"].close.assert_called_once()
            assert client._connection is None

    def test_close_no_connection(self, mock_dependencies):
        """Test close handles case when no connection exists."""
        client = ConcreteSQLiteClient()
        client._connection = None
        client.close()

        mock_dependencies["connection"].close.assert_not_called()

    def test_close_failure(self, mock_dependencies):
        """Test close handles errors gracefully."""
        mock_dependencies["connection"].close.side_effect = Exception("Close error")

        client = ConcreteSQLiteClient()
        client._connection = mock_dependencies["connection"]
        client.close()

        mock_dependencies["logger"].warning.assert_called()
        # Connection is not set to None if close() fails (it's inside try block)
        assert client._connection == mock_dependencies["connection"]

    def test_context_manager_success(self, mock_dependencies):
        """Test context manager usage."""
        client = ConcreteSQLiteClient()
        client._connection = mock_dependencies["connection"]

        with client:
            assert client._connection is not None

        mock_dependencies["connection"].close.assert_called_once()

    def test_context_manager_with_exception(self, mock_dependencies):
        """Test context manager rolls back on exception."""
        client = ConcreteSQLiteClient()
        client._connection = mock_dependencies["connection"]
        client._in_transaction = True

        with patch.object(client, "rollback") as mock_rollback:
            try:
                with client:
                    raise ValueError("Test error")
            except ValueError:
                pass

            # rollback is called in __exit__ and potentially in close() if in transaction
            # Since we're in a transaction, rollback is called in __exit__
            # and close() also calls rollback if in transaction
            assert mock_rollback.call_count >= 1
            mock_dependencies["connection"].close.assert_called_once()
