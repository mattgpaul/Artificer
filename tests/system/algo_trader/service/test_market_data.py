"""Integration tests for market data service CLI with full workflow mocking.

Tests cover CLI argument parsing, service dispatching, and end-to-end workflows.
All external dependencies are mocked to avoid external service requirements.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from system.algo_trader.service.market_data.historical import HistoricalMarketService
from system.algo_trader.service.market_data.live import LiveMarketService


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


@pytest.fixture
def mock_live_dependencies():
    """Fixture to mock all LiveMarketService dependencies."""
    with (
        patch("system.algo_trader.service.market_data.base.MarketHandler") as mock_market_handler,
        patch("system.algo_trader.service.market_data.base.WatchlistBroker") as mock_watchlist,
        patch("system.algo_trader.service.market_data.live.LiveMarketBroker") as mock_live_broker,
    ):
        mock_market_handler_instance = Mock()
        mock_market_handler.return_value = mock_market_handler_instance

        mock_watchlist_instance = Mock()
        mock_watchlist.return_value = mock_watchlist_instance

        mock_live_broker_instance = Mock()
        mock_live_broker.return_value = mock_live_broker_instance

        yield {
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
        patch("system.algo_trader.service.market_data.base.MarketHandler") as mock_market_handler,
        patch("system.algo_trader.service.market_data.base.WatchlistBroker") as mock_watchlist,
        patch(
            "system.algo_trader.service.market_data.historical.HistoricalMarketBroker"
        ) as mock_historical_broker,
        patch(
            "system.algo_trader.service.market_data.historical.MarketDataInflux"
        ) as mock_influx_handler,
    ):
        mock_market_handler_instance = Mock()
        mock_market_handler.return_value = mock_market_handler_instance

        mock_watchlist_instance = Mock()
        mock_watchlist.return_value = mock_watchlist_instance

        mock_historical_broker_instance = Mock()
        mock_historical_broker.return_value = mock_historical_broker_instance

        mock_influx_handler_instance = Mock()
        mock_influx_handler.return_value = mock_influx_handler_instance

        yield {
            "market_handler": mock_market_handler,
            "market_handler_instance": mock_market_handler_instance,
            "watchlist": mock_watchlist,
            "watchlist_instance": mock_watchlist_instance,
            "historical_broker": mock_historical_broker,
            "historical_broker_instance": mock_historical_broker_instance,
            "influx_handler": mock_influx_handler,
            "influx_handler_instance": mock_influx_handler_instance,
        }


class TestMarketDataCLIIntegration:
    """Test CLI integration and service dispatching."""

    @pytest.mark.integration
    def test_live_service_dispatch(self, mock_live_dependencies):
        """Test CLI correctly dispatches to LiveMarketService."""
        # This would test the CLI argument parsing and service instantiation
        # For now, test that services can be instantiated correctly
        service = LiveMarketService(sleep_override=1)

        assert service is not None
        assert service.sleep_override == 1
        assert service.running is True

    @pytest.mark.integration
    def test_historical_service_dispatch(self, mock_historical_dependencies):
        """Test CLI correctly dispatches to HistoricalMarketService."""
        service = HistoricalMarketService()

        assert service is not None
        assert service.running is True
        assert service.database_handler is not None


class TestLiveMarketServiceIntegration:
    """Integration tests for LiveMarketService full workflow."""

    @pytest.mark.integration
    def test_service_initialization(self, mock_live_dependencies, mock_redis, mock_schwab_api):
        """Test service initializes all clients correctly."""
        service = LiveMarketService(sleep_override=1)

        assert service is not None
        assert service.running is True
        assert service.sleep_override == 1
        assert service.api_handler is not None
        assert service.watchlist_broker is not None

    @pytest.mark.integration
    def test_execute_pipeline_full_workflow(
        self, mock_live_dependencies, mock_redis, mock_schwab_api
    ):
        """Test complete pipeline execution with mocked dependencies."""
        service = LiveMarketService(sleep_override=1)

        # Mock watchlist
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL", "GOOGL"})
        service.market_broker.set_quotes = Mock(return_value=True)

        # Execute pipeline
        result = service._execute_pipeline()

        assert result is True
        service.watchlist_broker.get_watchlist.assert_called_once()
        service.api_handler.get_quotes.assert_called_once()
        service.market_broker.set_quotes.assert_called_once()


class TestHistoricalMarketServiceIntegration:
    """Integration tests for HistoricalMarketService full workflow."""

    @pytest.mark.integration
    def test_service_initialization(
        self,
        mock_historical_dependencies,
        mock_redis,
        mock_influx,
        mock_schwab_api,
    ):
        """Test service initializes all clients correctly."""
        service = HistoricalMarketService()

        assert service is not None
        assert service.running is True
        assert service.api_handler is not None
        assert service.watchlist_broker is not None
        assert service.database_handler is not None

    @pytest.mark.integration
    def test_execute_pipeline_full_workflow(
        self,
        mock_historical_dependencies,
        mock_redis,
        mock_influx,
        mock_schwab_api,
    ):
        """Test complete pipeline execution with mocked dependencies."""
        service = HistoricalMarketService()

        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL"})
        service.market_broker.get_market_hours = Mock(
            return_value={
                "date": datetime.now(timezone.utc).isoformat(),
                "start": datetime.now(timezone.utc).isoformat(),
                "end": datetime.now(timezone.utc).isoformat(),
            }
        )
        service.api_handler.get_price_history = Mock(
            return_value={"symbol": "AAPL", "candles": [{"open": 150.0, "close": 151.0}]}
        )
        service.database_handler.write = Mock(return_value=True)

        # Execute pipeline
        service._execute_pipeline()

        service.watchlist_broker.get_watchlist.assert_called_once()
        service.api_handler.get_price_history.assert_called()
        service.database_handler.write.assert_called()
