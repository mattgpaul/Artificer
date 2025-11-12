"""Shared fixtures for SQLite bad ticker tests."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_mock_external_calls():
    """Automatically mock external calls to prevent hangs."""
    with (
        patch("system.algo_trader.sqlite.bad_ticker_client.os.makedirs"),
        patch("system.algo_trader.sqlite.bad_ticker_client.os.getenv", return_value=None),
    ):
        yield


@pytest.fixture
def mock_sqlite():
    """Fixture to mock sqlite3 module."""
    with patch("infrastructure.sqlite.sqlite.sqlite3") as mock_sqlite_module:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.execute.return_value = mock_cursor
        mock_cursor.rowcount = 0
        mock_sqlite_module.connect.return_value = mock_connection

        yield {
            "module": mock_sqlite_module,
            "connection": mock_connection,
            "cursor": mock_cursor,
        }


@pytest.fixture
def mock_logger():
    """Fixture to mock logger."""
    with patch("infrastructure.sqlite.sqlite.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_daemon_dependencies():
    """Fixture to mock all daemon dependencies."""
    with (
        patch("system.algo_trader.sqlite.bad_ticker_daemon.QueueBroker") as mock_queue_broker_class,
        patch("system.algo_trader.sqlite.bad_ticker_daemon.BadTickerClient") as mock_client_class,
        patch("system.algo_trader.sqlite.bad_ticker_daemon.get_logger") as mock_get_logger,
        patch("system.algo_trader.sqlite.bad_ticker_daemon.signal.signal") as mock_signal,
        patch("system.algo_trader.sqlite.bad_ticker_daemon.time.sleep") as mock_sleep,
    ):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_queue_broker = MagicMock()
        mock_queue_broker.get_queue_size.return_value = 0
        mock_queue_broker_class.return_value = mock_queue_broker

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        yield {
            "logger": mock_logger,
            "queue_broker": mock_queue_broker,
            "client": mock_client,
            "signal": mock_signal,
            "sleep": mock_sleep,
        }
