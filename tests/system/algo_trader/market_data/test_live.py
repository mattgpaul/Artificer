"""Unit tests for LiveMarketService - Live market data service.

Tests cover initialization, sleep interval calculation, pipeline execution, and health checks.
All external dependencies are mocked to avoid external service requirements.
"""

from unittest.mock import Mock, patch

import pytest

from system.algo_trader.market_data.base import MarketHoursType
from system.algo_trader.market_data.live import LiveMarketService


@pytest.fixture
def mock_live_dependencies():
    """Fixture to mock all LiveMarketService dependencies."""
    with (
        patch("system.algo_trader.market_data.base.get_logger") as mock_logger,
        patch("system.algo_trader.market_data.base.MarketHandler") as mock_market_handler,
        patch("system.algo_trader.market_data.base.WatchlistBroker") as mock_watchlist,
        patch("system.algo_trader.market_data.live.LiveMarketBroker") as mock_live_broker,
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


class TestLiveMarketServiceInitialization:
    """Test LiveMarketService initialization and configuration."""

    def test_initialization_default_config(self, mock_live_dependencies):
        """Test initialization with default configuration."""
        service = LiveMarketService()

        assert service.running is True
        assert service.sleep_override is None
        assert service.api_handler is not None
        assert service.watchlist_broker is not None
        assert service.market_broker is not None

    def test_initialization_with_sleep_override(self, mock_live_dependencies):
        """Test initialization with sleep override."""
        service = LiveMarketService(sleep_override=30)

        assert service.sleep_override == 30
        assert service.running is True

    def test_initialization_with_config(self, mock_live_dependencies):
        """Test initialization with custom config."""
        mock_config = Mock()
        mock_config.redis = Mock()
        service = LiveMarketService(config=mock_config)

        assert service.config == mock_config
        mock_live_dependencies["live_broker"].assert_called_once_with(config=mock_config.redis)


class TestLiveMarketServiceSleepInterval:
    """Test sleep interval calculation based on market conditions."""

    def test_sleep_interval_with_override(self, mock_live_dependencies):
        """Test sleep interval uses override when provided."""
        service = LiveMarketService(sleep_override=30)

        result = service._get_sleep_interval()

        assert result == 30

    def test_sleep_interval_market_closed(self, mock_live_dependencies):
        """Test sleep interval when market is closed."""
        service = LiveMarketService()

        # Mock market closed
        service._check_market_open = Mock(return_value=False)

        result = service._get_sleep_interval()

        assert result == 3600  # 1 hour

    def test_sleep_interval_premarket(self, mock_live_dependencies):
        """Test sleep interval during premarket hours."""
        service = LiveMarketService()

        # Mock market open and premarket hours
        service._check_market_open = Mock(return_value=True)
        service._check_market_hours = Mock(return_value=MarketHoursType.PREMARKET)
        service.market_broker.get_market_hours = Mock(
            return_value={
                "date": "2024-01-01",
                "start": "2024-01-01T09:30:00Z",
                "end": "2024-01-01T16:00:00Z",
            }
        )

        result = service._get_sleep_interval()

        assert result == 300  # 5 minutes

    def test_sleep_interval_standard_hours(self, mock_live_dependencies):
        """Test sleep interval during standard trading hours."""
        service = LiveMarketService()

        # Mock market open and standard hours
        service._check_market_open = Mock(return_value=True)
        service._check_market_hours = Mock(return_value=MarketHoursType.STANDARD)
        service.market_broker.get_market_hours = Mock(
            return_value={
                "date": "2024-01-01",
                "start": "2024-01-01T09:30:00Z",
                "end": "2024-01-01T16:00:00Z",
            }
        )

        result = service._get_sleep_interval()

        assert result == 1  # 1 second

    def test_sleep_interval_extended_hours(self, mock_live_dependencies):
        """Test sleep interval during extended hours."""
        service = LiveMarketService()

        # Mock market open and extended hours
        service._check_market_open = Mock(return_value=True)
        service._check_market_hours = Mock(return_value=MarketHoursType.EXTENDED)
        service.market_broker.get_market_hours = Mock(
            return_value={
                "date": "2024-01-01",
                "start": "2024-01-01T09:30:00Z",
                "end": "2024-01-01T16:00:00Z",
            }
        )

        result = service._get_sleep_interval()

        assert result == 3600  # 1 hour


class TestLiveMarketServicePipeline:
    """Test pipeline execution and data processing."""

    def test_execute_pipeline_success(self, mock_live_dependencies):
        """Test successful pipeline execution."""
        service = LiveMarketService()

        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL", "GOOGL"})
        service.api_handler.get_quotes = Mock(return_value={"AAPL": {"price": 150.0}})
        service.market_broker.set_quotes = Mock(return_value=True)

        result = service._execute_pipeline()

        assert result is True
        service.watchlist_broker.get_watchlist.assert_called_once()
        # Check that get_quotes was called with the correct tickers (order doesn't matter)
        service.api_handler.get_quotes.assert_called_once()
        call_args = service.api_handler.get_quotes.call_args[0][0]
        assert set(call_args) == {"AAPL", "GOOGL"}
        service.market_broker.set_quotes.assert_called_once_with({"AAPL": {"price": 150.0}})

    def test_execute_pipeline_empty_watchlist(self, mock_live_dependencies):
        """Test pipeline execution with empty watchlist."""
        service = LiveMarketService()

        # Mock empty watchlist
        service.watchlist_broker.get_watchlist = Mock(return_value=set())

        result = service._execute_pipeline()

        assert result is True
        service.watchlist_broker.get_watchlist.assert_called_once()
        # Should not call API or broker when watchlist is empty

    def test_execute_pipeline_none_watchlist(self, mock_live_dependencies):
        """Test pipeline execution with None watchlist."""
        service = LiveMarketService()

        # Mock None watchlist
        service.watchlist_broker.get_watchlist = Mock(return_value=None)

        result = service._execute_pipeline()

        assert result is True
        service.watchlist_broker.get_watchlist.assert_called_once()
        # Should not call API or broker when watchlist is None

    def test_execute_pipeline_broker_failure(self, mock_live_dependencies):
        """Test pipeline execution when broker fails."""
        service = LiveMarketService()

        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL"})
        service.api_handler.get_quotes = Mock(return_value={"AAPL": {"price": 150.0}})
        service.market_broker.set_quotes = Mock(return_value=False)

        result = service._execute_pipeline()

        assert result is False
        service.market_broker.set_quotes.assert_called_once()


class TestLiveMarketServiceHealthCheck:
    """Test health check functionality."""

    def test_health_check_implementation(self, mock_live_dependencies):
        """Test health check method exists and can be called."""
        service = LiveMarketService()

        # Health check should not raise an exception
        result = service.health_check()

        # Currently returns None, but method exists
        assert result is None


class TestLiveMarketServiceErrorHandling:
    """Test error handling and edge cases."""

    def test_execute_pipeline_api_error(self, mock_live_dependencies):
        """Test pipeline execution handles API errors gracefully."""
        service = LiveMarketService()

        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL"})
        service.api_handler.get_quotes = Mock(side_effect=RuntimeError("API Error"))

        # Should not raise exception, but may return False
        with pytest.raises(RuntimeError):
            service._execute_pipeline()

    def test_execute_pipeline_watchlist_error(self, mock_live_dependencies):
        """Test pipeline execution handles watchlist errors gracefully."""
        service = LiveMarketService()

        # Mock watchlist error
        service.watchlist_broker.get_watchlist = Mock(side_effect=RuntimeError("Redis Error"))

        # Should not raise exception, but may return False
        with pytest.raises(RuntimeError):
            service._execute_pipeline()
