"""Unit tests for MarketBase - Base class for market data services.

Tests cover initialization, signal handling, market hours management, and timing control.
All external dependencies are mocked to avoid external service requirements.
"""

import signal
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from system.algo_trader.market_data.base import MarketBase, MarketHoursType
from system.algo_trader.utils.schema import MarketHours


@pytest.fixture
def mock_base_dependencies():
    """Fixture to mock all base MarketBase dependencies."""
    with (
        patch("system.algo_trader.market_data.base.get_logger") as mock_logger,
        patch("system.algo_trader.market_data.base.MarketHandler") as mock_market_handler,
        patch("system.algo_trader.market_data.base.WatchlistBroker") as mock_watchlist,
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


class ConcreteMarketService(MarketBase):
    """Concrete implementation for testing MarketBase."""

    def __init__(self, sleep_override=None, config=None):
        """Initialize concrete market service for testing."""
        super().__init__(sleep_override, config)
        self._market_broker = Mock()

    @property
    def market_broker(self):
        """Return mock market broker for testing."""
        return self._market_broker

    def _get_sleep_interval(self) -> int:
        return 60

    def _execute_pipeline(self) -> bool:
        return True


class TestMarketBaseInitialization:
    """Test MarketBase initialization and configuration."""

    def test_initialization_default_config(self, mock_base_dependencies):
        """Test initialization with default configuration."""
        service = ConcreteMarketService()

        assert service.running is True
        assert service.sleep_override is None
        assert service.config is None
        assert service.api_handler is not None
        assert service.watchlist_broker is not None

    def test_initialization_with_sleep_override(self, mock_base_dependencies):
        """Test initialization with sleep override."""
        service = ConcreteMarketService(sleep_override=30)

        assert service.sleep_override == 30
        assert service.running is True

    def test_initialization_with_config(self, mock_base_dependencies):
        """Test initialization with custom config."""
        mock_config = Mock()
        service = ConcreteMarketService(config=mock_config)

        assert service.config == mock_config


class TestMarketBaseSignalHandling:
    """Test signal handling and graceful shutdown."""

    def test_signal_handlers_setup(self, mock_base_dependencies):
        """Test signal handlers are properly configured."""
        with patch("signal.signal") as mock_signal:
            ConcreteMarketService()

            # Verify signal handlers were set up
            assert mock_signal.call_count == 2
            calls = mock_signal.call_args_list
            assert calls[0][0][0] == signal.SIGTERM
            assert calls[1][0][0] == signal.SIGINT

    def test_shutdown_handler(self, mock_base_dependencies):
        """Test shutdown handler sets running flag to False."""
        service = ConcreteMarketService()
        assert service.running is True

        # Simulate signal
        service._shutdown_handler(signal.SIGTERM, None)

        assert service.running is False
        mock_base_dependencies["logger_instance"].info.assert_called()


class TestMarketBaseMarketHours:
    """Test market hours checking and classification."""

    def test_check_market_open_with_start(self, mock_base_dependencies):
        """Test market open check when start time is present."""
        service = ConcreteMarketService()
        hours_data = {"start": "09:30", "end": "16:00"}

        result = service._check_market_open(hours_data)

        assert result == (True, hours_data)

    def test_check_market_open_without_start(self, mock_base_dependencies):
        """Test market open check when start time is missing."""
        service = ConcreteMarketService()
        hours_data = {"end": "16:00"}

        result = service._check_market_open(hours_data)

        assert result is False

    def test_check_market_hours_premarket(self, mock_base_dependencies):
        """Test market hours classification for premarket."""
        service = ConcreteMarketService()

        # Create market hours with premarket time
        now = datetime.now(timezone.utc)
        date = now.date()
        start_time = now + timedelta(hours=1)  # Market opens in 1 hour
        end_time = now + timedelta(hours=8)  # Market closes in 8 hours

        hours = MarketHours(date=date, start=start_time, end=end_time)

        result = service._check_market_hours(hours)

        assert result == MarketHoursType.PREMARKET

    def test_check_market_hours_standard(self, mock_base_dependencies):
        """Test market hours classification for standard hours."""
        service = ConcreteMarketService()

        # Create market hours during standard trading
        now = datetime.now(timezone.utc)
        date = now.date()
        start_time = now - timedelta(hours=2)  # Market opened 2 hours ago
        end_time = now + timedelta(hours=4)  # Market closes in 4 hours

        hours = MarketHours(date=date, start=start_time, end=end_time)

        result = service._check_market_hours(hours)

        assert result == MarketHoursType.STANDARD

    def test_check_market_hours_extended(self, mock_base_dependencies):
        """Test market hours classification for extended hours."""
        service = ConcreteMarketService()

        # Create market hours outside trading time
        now = datetime.now(timezone.utc)
        date = now.date()
        start_time = now - timedelta(hours=10)  # Market opened 10 hours ago
        end_time = now - timedelta(hours=2)  # Market closed 2 hours ago

        hours = MarketHours(date=date, start=start_time, end=end_time)

        result = service._check_market_hours(hours)

        assert result == MarketHoursType.EXTENDED


class TestMarketBaseTiming:
    """Test timing control and sleep functionality."""

    def test_sleep_with_interrupt_check(self, mock_base_dependencies):
        """Test sleep functionality with interrupt checking."""
        service = ConcreteMarketService()

        # Test that the method can be called without error
        # Use a very short sleep duration to avoid long test times
        service._sleep_with_interrupt_check(0.001)

        # Verify _last_cycle_time was set
        assert hasattr(service, "_last_cycle_time")

    def test_sleep_respects_shutdown_flag(self, mock_base_dependencies):
        """Test sleep respects shutdown flag."""
        service = ConcreteMarketService()
        service.running = False

        # Should return immediately when running is False
        start_time = time.time()
        service._sleep_with_interrupt_check(1.0)
        end_time = time.time()

        # Should complete very quickly
        assert (end_time - start_time) < 0.1


class TestMarketBaseErrorHandling:
    """Test error handling and edge cases."""

    def test_setup_clients_error_handling(self, mock_base_dependencies):
        """Test error handling during client setup."""
        # Make MarketHandler raise an exception
        mock_base_dependencies["market_handler"].side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            ConcreteMarketService()

        mock_base_dependencies["logger_instance"].error.assert_called()

    def test_set_market_hours(self, mock_base_dependencies):
        """Test setting market hours."""
        service = ConcreteMarketService()
        mock_api_handler = Mock()
        service.api_handler = mock_api_handler

        # Mock market hours response
        mock_api_handler.get_market_hours.return_value = {"start": "09:30", "end": "16:00"}

        service._set_market_hours()

        # Verify API was called and broker was updated
        mock_api_handler.get_market_hours.assert_called_once()
        service.market_broker.set_market_hours.assert_called_once_with(
            {"start": "09:30", "end": "16:00"}
        )
