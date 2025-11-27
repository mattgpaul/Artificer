"""Unit tests for HistoricalMarketService - Historical market data service.

Tests cover initialization, intraday intervals, sleep calculation, frequency handling,
and pipeline execution. All external dependencies are mocked to avoid external service requirements.
"""

from unittest.mock import Mock, patch

import pytest

from system.algo_trader.service.market_data.base import MarketHoursType
from system.algo_trader.service.market_data.historical import (
    HistoricalMarketService,
    IntradayInterval,
)


class TestHistoricalMarketServiceInitialization:
    """Test HistoricalMarketService initialization and configuration."""

    def test_initialization_default_config(self, mock_historical_dependencies):
        """Test initialization with default configuration."""
        service = HistoricalMarketService()

        assert service.running is True
        assert service.sleep_override is None
        assert service.api_handler is not None
        assert service.watchlist_broker is not None
        assert service.market_broker is not None
        assert service.database_handler is not None

    def test_initialization_with_sleep_override(self, mock_historical_dependencies):
        """Test initialization with sleep override (should be ignored)."""
        service = HistoricalMarketService(sleep_override=30)

        assert service.sleep_override is None  # Should be reset to None
        assert service.running is True
        mock_historical_dependencies["logger_instance"].warning.assert_called()

    def test_initialization_with_config(self, mock_historical_dependencies):
        """Test initialization with custom config."""
        mock_config = Mock()
        mock_config.redis = Mock()
        mock_config.influxdb = Mock()
        mock_config.influxdb.database = "custom_database"

        service = HistoricalMarketService(config=mock_config)

        assert service.config == mock_config
        mock_historical_dependencies["historical_broker"].assert_called_once_with(
            config=mock_config.redis
        )
        mock_historical_dependencies["influx_handler"].assert_called_once_with(
            database="custom_database", config=mock_config.influxdb
        )

    def test_initialization_with_config_no_database(self, mock_historical_dependencies):
        """Test initialization with config but no database specified (fallback to default)."""
        mock_config = Mock()
        mock_config.redis = Mock()
        mock_config.influxdb = Mock()
        mock_config.influxdb.database = None  # No database specified

        service = HistoricalMarketService(config=mock_config)

        assert service.config == mock_config
        mock_historical_dependencies["historical_broker"].assert_called_once_with(
            config=mock_config.redis
        )
        mock_historical_dependencies["influx_handler"].assert_called_once_with(
            database="market_data", config=mock_config.influxdb
        )


class TestHistoricalMarketServiceIntradayInterval:
    """Test intraday interval calculation based on market conditions."""

    def test_check_intraday_interval_market_closed(self, mock_historical_dependencies):
        """Test intraday interval when market is closed."""
        service = HistoricalMarketService()

        # Mock market closed
        service._check_market_open = Mock(return_value=False)

        result = service._check_intraday_interval()

        assert result == IntradayInterval.MIN30

    def test_check_intraday_interval_non_standard_hours(self, mock_historical_dependencies):
        """Test intraday interval during non-standard hours."""
        service = HistoricalMarketService()

        # Mock market open but non-standard hours
        service._check_market_open = Mock(return_value=True)
        service._check_market_hours = Mock(return_value=MarketHoursType.PREMARKET)
        service.market_broker.get_market_hours = Mock(
            return_value={
                "date": "2024-01-01",
                "start": "2024-01-01T09:30:00Z",
                "end": "2024-01-01T16:00:00Z",
            }
        )

        result = service._check_intraday_interval()

        assert result == IntradayInterval.MIN30

    def test_check_intraday_interval_minute_1(self, mock_historical_dependencies):
        """Test intraday interval for 1-minute intervals."""
        service = HistoricalMarketService()

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

        # Mock current minute that's only divisible by 1
        with patch("system.algo_trader.service.market_data.historical.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.minute = 7  # 7 is only divisible by 1 (not by 5, 10, 15, or 30)
            mock_datetime.now.return_value = mock_now

            result = service._check_intraday_interval()

            assert result == IntradayInterval.MIN1

    def test_check_intraday_interval_minute_5(self, mock_historical_dependencies):
        """Test intraday interval for 5-minute intervals."""
        service = HistoricalMarketService()

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

        # Mock current minute divisible by 5 but not by larger intervals
        with patch("system.algo_trader.service.market_data.historical.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.minute = 5  # Divisible by 5, not by 10, 15, or 30
            mock_datetime.now.return_value = mock_now

            result = service._check_intraday_interval()

            assert result == IntradayInterval.MIN5


class TestHistoricalMarketServiceSleepInterval:
    """Test sleep interval calculation."""

    def test_get_sleep_interval_market_closed(self, mock_historical_dependencies):
        """Test sleep interval when market is closed."""
        service = HistoricalMarketService()

        # Mock market closed
        service._check_market_open = Mock(return_value=False)

        result = service._get_sleep_interval()

        assert result == 3600  # 1 hour

    def test_get_sleep_interval_non_standard_hours(self, mock_historical_dependencies):
        """Test sleep interval during non-standard hours."""
        service = HistoricalMarketService()

        # Mock market open but non-standard hours
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

        assert result == 3600  # 1 hour

    def test_get_sleep_interval_standard_hours(self, mock_historical_dependencies):
        """Test sleep interval during standard hours."""
        service = HistoricalMarketService()

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

        assert result == 60  # 1 minute


class TestHistoricalMarketServiceFrequencies:
    """Test frequency calculation for different intervals."""

    def test_get_frequencies_min1(self, mock_historical_dependencies):
        """Test frequency calculation for 1-minute interval."""
        service = HistoricalMarketService()

        result = service._get_frequencies(IntradayInterval.MIN1)

        assert result == [1]

    def test_get_frequencies_min5(self, mock_historical_dependencies):
        """Test frequency calculation for 5-minute interval."""
        service = HistoricalMarketService()

        result = service._get_frequencies(IntradayInterval.MIN5)

        assert result == [1, 5]

    def test_get_frequencies_min30(self, mock_historical_dependencies):
        """Test frequency calculation for 30-minute interval."""
        service = HistoricalMarketService()

        result = service._get_frequencies(IntradayInterval.MIN30)

        assert result == [1, 5, 10, 15, 30]


class TestHistoricalMarketServicePipeline:
    """Test pipeline execution and data processing."""

    def test_execute_pipeline_success(self, mock_historical_dependencies):
        """Test successful pipeline execution."""
        service = HistoricalMarketService()

        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL"})
        service._check_intraday_interval = Mock(return_value=IntradayInterval.MIN1)
        service._get_frequencies = Mock(return_value=[1])
        service.api_handler.get_price_history = Mock(
            return_value={"symbol": "AAPL", "candles": [{"open": 150.0, "close": 151.0}]}
        )
        service.database_handler.write = Mock(return_value=True)

        service._execute_pipeline()

        # Verify all methods were called
        service.watchlist_broker.get_watchlist.assert_called_once()
        service._check_intraday_interval.assert_called_once()
        service._get_frequencies.assert_called_once_with(IntradayInterval.MIN1)
        service.api_handler.get_price_history.assert_called_once()
        service.database_handler.write.assert_called_once()

    def test_execute_pipeline_multiple_tickers_frequencies(self, mock_historical_dependencies):
        """Test pipeline execution with multiple tickers and frequencies."""
        service = HistoricalMarketService()

        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL", "GOOGL"})
        service._check_intraday_interval = Mock(return_value=IntradayInterval.MIN5)
        service._get_frequencies = Mock(return_value=[1, 5])
        service.api_handler.get_price_history = Mock(
            return_value={"symbol": "AAPL", "candles": [{"open": 150.0, "close": 151.0}]}
        )
        service.database_handler.write = Mock(return_value=True)

        service._execute_pipeline()

        # Should call API for each ticker/frequency combination
        expected_calls = 4  # 2 tickers * 2 frequencies
        assert service.api_handler.get_price_history.call_count == expected_calls
        assert service.database_handler.write.call_count == expected_calls

    def test_execute_pipeline_empty_watchlist(self, mock_historical_dependencies):
        """Test pipeline execution with empty watchlist."""
        service = HistoricalMarketService()

        # Mock empty watchlist
        service.watchlist_broker.get_watchlist = Mock(return_value=set())
        service.market_broker.get_market_hours = Mock(
            return_value={
                "date": "2024-01-01",
                "start": "2024-01-01T09:30:00Z",
                "end": "2024-01-01T16:00:00Z",
            }
        )
        service._check_market_open = Mock(return_value=True)
        service._check_market_hours = Mock(return_value=MarketHoursType.STANDARD)

        service._execute_pipeline()

        # Should not call API or database when watchlist is empty
        service.api_handler.get_price_history.assert_not_called()
        service.database_handler.write.assert_not_called()


class TestHistoricalMarketServiceErrorHandling:
    """Test error handling and edge cases."""

    def test_execute_pipeline_api_error(self, mock_historical_dependencies):
        """Test pipeline execution handles API errors gracefully."""
        service = HistoricalMarketService()

        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL"})
        service._check_intraday_interval = Mock(return_value=IntradayInterval.MIN1)
        service._get_frequencies = Mock(return_value=[1])
        service.api_handler.get_price_history = Mock(side_effect=RuntimeError("API Error"))

        # Should return False when API error occurs
        result = service._execute_pipeline()
        assert result is False

    def test_execute_pipeline_database_error(self, mock_historical_dependencies):
        """Test pipeline execution handles database errors gracefully."""
        service = HistoricalMarketService()

        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL"})
        service._check_intraday_interval = Mock(return_value=IntradayInterval.MIN1)
        service._get_frequencies = Mock(return_value=[1])
        service.api_handler.get_price_history = Mock(
            return_value={"symbol": "AAPL", "candles": [{"open": 150.0, "close": 151.0}]}
        )
        service.database_handler.write = Mock(side_effect=RuntimeError("Database Error"))

        # Should return False when database error occurs
        result = service._execute_pipeline()
        assert result is False
