"""Shared fixtures for populate datasource tests."""

from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.datasource.populate.fundamentals.handler import (
    FundamentalsArgumentHandler,
)
from system.algo_trader.datasource.populate.ohlcv.handler import OHLCVArgumentHandler


@pytest.fixture(autouse=True)
def auto_mock_external_calls():
    """Automatically mock external calls to prevent hangs."""
    with (
        patch("system.algo_trader.datasource.populate.fundamentals.processor.time.sleep"),
        patch("system.algo_trader.datasource.populate.ohlcv.processor.time.sleep"),
    ):
        yield


@pytest.fixture
def mock_logger():
    """Fixture to mock logger."""
    with patch(
        "system.algo_trader.datasource.populate.argument_base.get_logger"
    ) as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def fundamentals_handler(mock_logger):
    """Fixture to create a FundamentalsArgumentHandler instance."""
    return FundamentalsArgumentHandler()


@pytest.fixture
def ohlcv_handler(mock_logger):
    """Fixture to create an OHLCVArgumentHandler instance."""
    return OHLCVArgumentHandler()


@pytest.fixture
def mock_tickers():
    """Fixture to mock Tickers class."""
    with (
        patch("system.algo_trader.datasource.populate.ohlcv.handler.Tickers") as mock_ohlcv_tickers,
        patch(
            "system.algo_trader.datasource.populate.fundamentals.handler.Tickers"
        ) as mock_fundamentals_tickers,
    ):
        mock_tickers_instance = MagicMock()
        mock_ohlcv_tickers.return_value = mock_tickers_instance
        mock_fundamentals_tickers.return_value = mock_tickers_instance
        yield mock_tickers_instance


@pytest.fixture
def mock_bad_ticker_client():
    """Fixture to mock BadTickerClient."""
    with patch(
        "system.algo_trader.datasource.populate.fundamentals.handler.BadTickerClient"
    ) as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.is_bad_ticker.return_value = False
        mock_client_class.return_value = mock_client_instance
        yield mock_client_instance


@pytest.fixture
def mock_ohlcv_bad_ticker_client():
    """Fixture to mock BadTickerClient for OHLCV tests."""
    with patch(
        "system.algo_trader.datasource.populate.ohlcv.handler.BadTickerClient"
    ) as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.is_bad_ticker.return_value = False
        mock_client_instance.get_bad_tickers.return_value = []
        mock_client_instance.remove_bad_ticker.return_value = True
        mock_client_class.return_value = mock_client_instance
        yield mock_client_instance


@pytest.fixture
def mock_queue_broker():
    """Fixture to mock QueueBroker."""
    with patch(
        "system.algo_trader.datasource.populate.fundamentals.processor.QueueBroker"
    ) as mock_broker_class:
        mock_broker_instance = MagicMock()
        mock_broker_instance.enqueue.return_value = True
        mock_broker_class.return_value = mock_broker_instance
        yield mock_broker_instance


@pytest.fixture
def mock_thread_manager():
    """Fixture to mock ThreadManager."""
    with patch(
        "system.algo_trader.datasource.populate.fundamentals.processor.ThreadManager"
    ) as mock_manager_class:
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_active_thread_count.return_value = 0
        mock_manager_instance.get_results_summary.return_value = {"successful": 0, "failed": 0}
        mock_manager_instance.wait_for_all_threads.return_value = None
        mock_manager_class.return_value = mock_manager_instance
        yield mock_manager_instance


@pytest.fixture
def mock_ohlcv_thread_manager():
    """Fixture to mock ThreadManager for OHLCV tests."""
    with patch(
        "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
    ) as mock_manager_class:
        mock_manager_instance = MagicMock()
        mock_manager_instance.config.max_threads = 10
        mock_manager_instance.get_active_thread_count.return_value = 0
        mock_manager_instance.get_results_summary.return_value = {
            "successful": 0,
            "failed": 0,
            "running": 0,
            "total": 0,
        }
        mock_manager_instance.wait_for_all_threads.return_value = None
        mock_manager_instance.cleanup_dead_threads.return_value = 0
        mock_manager_class.return_value = mock_manager_instance
        yield mock_manager_instance
