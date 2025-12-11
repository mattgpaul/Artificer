"""Shared fixtures for MySQL tests."""

import sys
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_mock_external_calls():
    """Automatically mock external calls to prevent hangs."""
    # Patch os operations for MySQL clients
    patches = []
    if "system.algo_trader.mysql.bad_ticker_client" in sys.modules:
        patches.append(
            patch("system.algo_trader.mysql.bad_ticker_client.os.getenv", return_value=None)
        )

    if "system.algo_trader.mysql.fundamentals_client" in sys.modules:
        patches.append(
            patch("system.algo_trader.mysql.fundamentals_client.os.getenv", return_value=None)
        )

    if patches:
        with ExitStack() as stack:
            for patch_obj in patches:
                stack.enter_context(patch_obj)
            yield
    else:
        yield


@pytest.fixture
def mock_mysql():
    """Fixture to mock pymysql module."""
    with patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql_module:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.return_value = 0
        mock_cursor.rowcount = 0
        mock_pymysql_module.connect.return_value = mock_connection

        yield {
            "module": mock_pymysql_module,
            "connection": mock_connection,
            "cursor": mock_cursor,
        }


@pytest.fixture
def mock_logger():
    """Fixture to mock logger."""
    with patch("infrastructure.mysql.mysql.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_mysql_config():
    """Fixture to mock MySQLConfig for bad_ticker_client tests."""
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
        yield mock_config


@pytest.fixture
def mock_mysql_daemon_dependencies():
    """Fixture to mock all MySQL daemon dependencies."""
    with (
        patch("system.algo_trader.mysql.mysql_daemon.QueueBroker") as mock_queue_broker_class,
        patch(
            "system.algo_trader.mysql.mysql_daemon.BadTickerClient"
        ) as mock_bad_ticker_client_class,
        patch(
            "system.algo_trader.mysql.mysql_daemon.FundamentalsClient"
        ) as mock_fundamentals_client_class,
        patch("system.algo_trader.mysql.mysql_daemon.get_logger") as mock_get_logger,
        patch("system.algo_trader.mysql.mysql_daemon.signal.signal") as mock_signal,
        patch("system.algo_trader.mysql.mysql_daemon.time.sleep") as mock_sleep,
    ):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_queue_broker = MagicMock()
        mock_queue_broker.get_queue_size.return_value = 0
        mock_queue_broker.dequeue.return_value = None
        mock_queue_broker.get_data.return_value = None
        mock_queue_broker_class.return_value = mock_queue_broker

        mock_bad_ticker_client = MagicMock()
        mock_bad_ticker_client.log_bad_ticker.return_value = True
        mock_bad_ticker_client_class.return_value = mock_bad_ticker_client

        mock_fundamentals_client = MagicMock()
        mock_fundamentals_client.upsert_fundamentals.return_value = True
        mock_fundamentals_client_class.return_value = mock_fundamentals_client

        yield {
            "logger": mock_logger,
            "queue_broker": mock_queue_broker,
            "bad_ticker_client": mock_bad_ticker_client,
            "fundamentals_client": mock_fundamentals_client,
            "signal": mock_signal,
            "sleep": mock_sleep,
        }
