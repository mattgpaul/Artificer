"""Unit tests for BaseTimescaleDBClient - TimescaleDB database operations.

Tests cover client initialization, connection management, and health checks.
All psycopg2 interactions are mocked via fixtures in conftest.py so that
tests do not require a running TimescaleDB instance.
"""

from __future__ import annotations

import pytest

from infrastructure.config import TimescaleDBConfig
from infrastructure.timescaledb.timescaledb import BaseTimescaleDBClient

# All tests in this module are unit tests exercising the Python wrapper only.
pytestmark = pytest.mark.unit


class TestTimescaleDBClientInitialization:
    """Test BaseTimescaleDBClient initialization and configuration."""

    def test_initialization_with_custom_config(self, mock_psycopg2_connect_success, mock_logger):
        """Client should copy fields from an explicit TimescaleDBConfig."""
        config = TimescaleDBConfig(
            host="db.example.com",
            port=55432,
            user="ts_user",
            password="ts_pass",
            database="ts_db",
        )

        client = BaseTimescaleDBClient(config=config)

        assert client.host == "db.example.com"
        assert client.port == 55432
        assert client.user == "ts_user"
        assert client.password == "ts_pass"
        assert client.database == "ts_db"

    def test_initialization_uses_default_config_when_not_provided(
        self,
        timescaledb_env_from_vars,
        mock_psycopg2_connect_success,
        mock_logger,
    ):
        """Client should construct TimescaleDBConfig when config is omitted."""
        client = BaseTimescaleDBClient()

        # Values should be sourced from TimescaleDBConfig, which in turn reads env vars.
        assert client.host == "env-host"
        assert client.port == 5433
        assert client.user == "env-user"
        assert client.password == "env-pass"
        assert client.database == "env-db"
    def test_initialization_from_env_vars(
        self, timescaledb_env_from_vars, mock_psycopg2_connect_success, mock_logger
    ):
        """Client should respect values loaded from environment variables via TimescaleDBConfig."""
        config = TimescaleDBConfig()
        client = BaseTimescaleDBClient(config=config)

        assert client.host == "env-host"
        assert client.port == 5433
        assert client.user == "env-user"
        assert client.password == "env-pass"
        assert client.database == "env-db"


class TestTimescaleDBClientConnectionManagement:
    """Test BaseTimescaleDBClient connection lifecycle."""

    def test_get_connection_creates_and_reuses_connection(
        self,
        mock_psycopg2_connect_success,
        mock_logger,
    ):
        """_get_connection should create a connection once and then reuse it."""
        config = TimescaleDBConfig(
            host="db.example.com",
            port=55432,
            user="ts_user",
            password="ts_pass",
            database="ts_db",
        )
        client = BaseTimescaleDBClient(config=config)

        conn1 = client._get_connection()
        conn2 = client._get_connection()

        assert conn1 is conn2
        mock_psycopg2_connect_success["connect"].assert_called_once_with(
            host="db.example.com",
            port=55432,
            database="ts_db",
            user="ts_user",
            password="ts_pass",
        )

    def test_close_connection_closes_and_clears_connection(
        self,
        mock_psycopg2_connect_success,
        mock_logger,
    ):
        """_close_connection should close the active connection and reset the handle."""
        config = TimescaleDBConfig(
            host="db.example.com",
            port=55432,
            user="ts_user",
            password="ts_pass",
            database="ts_db",
        )
        client = BaseTimescaleDBClient(config=config)

        conn = client._get_connection()
        assert conn is mock_psycopg2_connect_success["connection"]

        client._close_connection()

        mock_psycopg2_connect_success["connection"].close.assert_called_once()
        assert client._connection is None

    def test_close_connection_is_noop_when_no_connection(self, mock_logger):
        """_close_connection should be safe to call when no connection exists."""
        client = BaseTimescaleDBClient()

        # Should not raise and should leave _connection as None.
        client._close_connection()
        assert client._connection is None


class TestTimescaleDBClientPing:
    """Test BaseTimescaleDBClient health checks."""

    def test_ping_success_uses_health_query_and_returns_true(
        self,
        mock_psycopg2_connect_success,
        mock_logger,
    ):
        """Ping should execute a simple health query and return True on success."""
        config = TimescaleDBConfig(
            host="db.example.com",
            port=55432,
            user="ts_user",
            password="ts_pass",
            database="ts_db",
        )
        client = BaseTimescaleDBClient(config=config)

        result = client.ping()

        assert result is True
        # The mocked connection exposes only a cursor-based interface; this
        # expectation encodes the desired implementation: use a trivial
        # query like SELECT 1 instead of driver-specific ping methods.
        mock_psycopg2_connect_success["cursor"].execute.assert_called_once_with("SELECT 1")

    def test_ping_failure_returns_false_on_exception(
        self,
        mock_psycopg2_connect_failure,
        mock_logger,
    ):
        """Ping should return False when the health check raises an exception."""
        config = TimescaleDBConfig(
            host="db.example.com",
            port=55432,
            user="ts_user",
            password="ts_pass",
            database="ts_db",
        )
        client = BaseTimescaleDBClient(config=config)

        result = client.ping()

        assert result is False

    def test_ping_returns_false_when_connect_raises(
        self,
        mock_psycopg2_connect_exception,
        mock_logger,
    ):
        """Ping should return False when the initial connection attempt fails."""
        client = BaseTimescaleDBClient()

        result = client.ping()

        assert result is False
        # Connection handle should remain unset when connect() raises.
        assert client._connection is None
