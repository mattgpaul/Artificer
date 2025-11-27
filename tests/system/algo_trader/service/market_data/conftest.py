"""Shared fixtures for market data service tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("system.algo_trader.service.market_data.base.get_logger") as mock_logger_func:
        mock_logger_instance = Mock()
        mock_logger_func.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_base_dependencies():
    """Fixture to mock all base MarketBase dependencies."""
    with (
        patch("system.algo_trader.service.market_data.base.get_logger") as mock_logger,
        patch("system.algo_trader.service.market_data.base.MarketHandler") as mock_market_handler,
        patch("system.algo_trader.service.market_data.base.WatchlistBroker") as mock_watchlist,
    ):
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance

        mock_market_handler_instance = Mock()
        mock_market_handler.return_value = mock_market_handler_instance

        mock_watchlist_instance = Mock()
        mock_watchlist.return_value = mock_watchlist_instance

        yield {
            "logger": mock_logger,
            "logger_instance": mock_logger_instance,
            "market_handler": mock_market_handler,
            "market_handler_instance": mock_market_handler_instance,
            "watchlist": mock_watchlist,
            "watchlist_instance": mock_watchlist_instance,
        }


@pytest.fixture
def mock_live_dependencies():
    """Fixture to mock all LiveMarketService dependencies."""
    with (
        patch("system.algo_trader.service.market_data.base.get_logger") as mock_logger,
        patch("system.algo_trader.service.market_data.base.MarketHandler") as mock_market_handler,
        patch("system.algo_trader.service.market_data.base.WatchlistBroker") as mock_watchlist,
        patch("system.algo_trader.service.market_data.live.LiveMarketBroker") as mock_live_broker,
    ):
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance

        mock_market_handler_instance = Mock()
        mock_market_handler.return_value = mock_market_handler_instance

        mock_watchlist_instance = Mock()
        mock_watchlist.return_value = mock_watchlist_instance

        mock_live_broker_instance = Mock()
        mock_live_broker.return_value = mock_live_broker_instance

        yield {
            "logger": mock_logger,
            "logger_instance": mock_logger_instance,
            "market_handler": mock_market_handler,
            "market_handler_instance": mock_market_handler_instance,
            "watchlist": mock_watchlist,
            "watchlist_instance": mock_watchlist_instance,
            "live_broker": mock_live_broker,
            "live_broker_instance": mock_live_broker_instance,
        }


@pytest.fixture
def mock_historical_dependencies():
    """Fixture to mock all HistoricalMarketService dependencies."""
    with (
        patch("system.algo_trader.service.market_data.base.get_logger") as mock_logger,
        patch("system.algo_trader.service.market_data.base.MarketHandler") as mock_market_handler,
        patch("system.algo_trader.service.market_data.base.WatchlistBroker") as mock_watchlist,
        patch(
            "system.algo_trader.service.market_data.historical.HistoricalMarketBroker"
        ) as mock_historical_broker,
        patch(
            "system.algo_trader.service.market_data.historical.MarketDataInflux"
        ) as mock_influx_handler,
    ):
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance

        mock_market_handler_instance = Mock()
        mock_market_handler.return_value = mock_market_handler_instance

        mock_watchlist_instance = Mock()
        mock_watchlist.return_value = mock_watchlist_instance

        mock_historical_broker_instance = Mock()
        mock_historical_broker.return_value = mock_historical_broker_instance

        mock_influx_handler_instance = Mock()
        mock_influx_handler.return_value = mock_influx_handler_instance

        yield {
            "logger": mock_logger,
            "logger_instance": mock_logger_instance,
            "market_handler": mock_market_handler,
            "market_handler_instance": mock_market_handler_instance,
            "watchlist": mock_watchlist,
            "watchlist_instance": mock_watchlist_instance,
            "historical_broker": mock_historical_broker,
            "historical_broker_instance": mock_historical_broker_instance,
            "influx_handler": mock_influx_handler,
            "influx_handler_instance": mock_influx_handler_instance,
        }


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("redis.Redis") as mock:
        yield mock.return_value


@pytest.fixture
def mock_influx():
    """Mock InfluxDB client for testing."""
    with patch("influxdb_client_3.InfluxDBClient3") as mock:
        yield mock.return_value


@pytest.fixture
def mock_schwab_api():
    """Mock Schwab API handler for testing."""
    with patch("system.algo_trader.schwab.market_handler.MarketHandler") as mock:
        mock_handler = mock.return_value
        mock_handler.get_quotes.return_value = {
            "AAPL": {"symbol": "AAPL", "lastPrice": 150.0},
            "GOOGL": {"symbol": "GOOGL", "lastPrice": 2800.0},
        }
        mock_handler.get_market_hours.return_value = {
            "start": datetime.now(timezone.utc).isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
        }
        yield mock_handler

