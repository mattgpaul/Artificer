"""Shared fixtures for SQLite tests."""

import sys
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_mock_external_calls():
    """Automatically mock external calls to prevent hangs."""
    # Patch os operations for bad_ticker_client (needed by bad_ticker tests)
    # Note: fundamentals_client patches are handled via mock_fundamentals_os fixture
    # Note: fundamentals_daemon.time.sleep is patched in mock_fundamentals_daemon_dependencies
    # Only patch bad_ticker_client if the module is loaded (for bad_ticker tests)
    patches = []
    if "system.algo_trader.sqlite.bad_ticker_client" in sys.modules:
        patches.extend(
            [
                patch("system.algo_trader.sqlite.bad_ticker_client.os.makedirs"),
                patch("system.algo_trader.sqlite.bad_ticker_client.os.getenv", return_value=None),
            ]
        )

    if patches:
        with ExitStack() as stack:
            for patch_obj in patches:
                stack.enter_context(patch_obj)
            yield
    else:
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
def mock_fundamentals_os():
    """Fixture to mock os operations for fundamentals_client tests."""
    with (
        patch("system.algo_trader.sqlite.fundamentals_client.os.makedirs"),
        patch("system.algo_trader.sqlite.fundamentals_client.os.getenv", return_value=None),
    ):
        yield


@pytest.fixture
def mock_sqlite_config():
    """Fixture to mock SQLiteConfig for bad_ticker_client tests."""
    with patch("infrastructure.config.SQLiteConfig") as mock_config_class:
        mock_config = MagicMock()
        mock_config.db_path = "./data/algo_trader.db"
        mock_config.timeout = 30
        mock_config.isolation_level = "DEFERRED"
        mock_config_class.return_value = mock_config
        yield mock_config


@pytest.fixture
def mock_daemon_dependencies():
    """Fixture to mock all bad ticker daemon dependencies."""
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


@pytest.fixture
def mock_fundamentals_daemon_dependencies():
    """Fixture to mock all fundamentals daemon dependencies."""
    with (
        patch(
            "system.algo_trader.sqlite.fundamentals_daemon.QueueBroker"
        ) as mock_queue_broker_class,
        patch(
            "system.algo_trader.sqlite.fundamentals_daemon.FundamentalsClient"
        ) as mock_client_class,
        patch("system.algo_trader.sqlite.fundamentals_daemon.get_logger") as mock_get_logger,
        patch("system.algo_trader.sqlite.fundamentals_daemon.signal.signal") as mock_signal,
        patch("system.algo_trader.sqlite.fundamentals_daemon.time.sleep") as mock_sleep,
    ):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_queue_broker = MagicMock()
        mock_queue_broker.get_queue_size.return_value = 0
        mock_queue_broker.dequeue.return_value = None
        mock_queue_broker.get_data.return_value = None
        mock_queue_broker_class.return_value = mock_queue_broker

        mock_client = MagicMock()
        mock_client.upsert_fundamentals.return_value = True
        mock_client_class.return_value = mock_client

        yield {
            "logger": mock_logger,
            "queue_broker": mock_queue_broker,
            "client": mock_client,
            "signal": mock_signal,
            "sleep": mock_sleep,
        }
