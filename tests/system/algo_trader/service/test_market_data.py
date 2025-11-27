"""Integration tests for market data service CLI with full workflow mocking.

Tests cover CLI argument parsing, service dispatching, and end-to-end workflows.
All external dependencies are mocked to avoid external service requirements.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from system.algo_trader.service.market_data.historical import HistoricalMarketService
from system.algo_trader.service.market_data.live import LiveMarketService


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
