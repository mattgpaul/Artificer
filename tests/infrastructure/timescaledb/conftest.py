"""Shared fixtures for TimescaleDB client tests.

All psycopg2 interactions and logging are mocked here so that unit tests
can exercise BaseTimescaleDBClient behavior without requiring a real
TimescaleDB instance.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_logger() -> MagicMock:
    """Mock logger used by BaseTimescaleDBClient."""
    with patch("infrastructure.timescaledb.timescaledb.get_logger") as mock_get_logger:
        logger = MagicMock()
        mock_get_logger.return_value = logger
        yield logger


@pytest.fixture
def mock_psycopg2_connect_success() -> dict[str, Any]:
    """Mock psycopg2.connect for successful connection and health checks.

    The mocked connection only exposes a cursor-based interface to
    encourage the implementation to use a simple health query
    (e.g. SELECT 1) rather than non-portable connection methods.
    """
    with patch("infrastructure.timescaledb.timescaledb.psycopg2.connect") as mock_connect:
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.execute.return_value = None

        connection = MagicMock(spec=["cursor", "close"])
        connection.cursor.return_value = cursor

        mock_connect.return_value = connection

        yield {
            "connect": mock_connect,
            "connection": connection,
            "cursor": cursor,
        }


@pytest.fixture
def mock_psycopg2_connect_failure() -> dict[str, Any]:
    """Mock psycopg2.connect where the health check query fails."""
    with patch("infrastructure.timescaledb.timescaledb.psycopg2.connect") as mock_connect:
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.execute.side_effect = Exception("TimescaleDB error")

        connection = MagicMock(spec=["cursor", "close"])
        connection.cursor.return_value = cursor

        mock_connect.return_value = connection

        yield {
            "connect": mock_connect,
            "connection": connection,
            "cursor": cursor,
        }


@pytest.fixture
def mock_psycopg2_connect_exception() -> dict[str, Any]:
    """Mock psycopg2.connect to raise an exception on initial connection.

    This fixture is used to validate that the client handles connection
    failures gracefully and does not retain a half-initialized connection.
    """
    with patch("infrastructure.timescaledb.timescaledb.psycopg2.connect") as mock_connect:
        mock_connect.side_effect = Exception("Unable to connect to TimescaleDB")
        yield {
            "connect": mock_connect,
        }


@pytest.fixture
def timescaledb_env_from_vars() -> None:
    """Provide TimescaleDB settings via environment variables for config tests."""
    with patch.dict(
        os.environ,
        {
            "TIMESCALEDB_HOST": "env-host",
            "TIMESCALEDB_PORT": "5433",
            "TIMESCALEDB_USER": "env-user",
            "TIMESCALEDB_PASSWORD": "env-pass",
            "TIMESCALEDB_DATABASE": "env-db",
        },
        clear=False,
    ):
        yield
