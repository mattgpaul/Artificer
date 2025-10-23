"""Unit tests for HistoricalMarketBroker - Historical Market Data Management

Tests cover historical candles storage/retrieval and market hours management.
All Redis operations are mocked to avoid requiring a Redis server.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.redis.historical_market import HistoricalMarketBroker


class TestHistoricalMarketBrokerInitialization:
    """Test HistoricalMarketBroker initialization"""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection"""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger"""
        with patch("system.algo_trader.redis.historical_market.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_initialization_default_ttl(self, mock_redis, mock_logger):
        """Test initialization with default TTL of 24 hours"""
        broker = HistoricalMarketBroker()

        assert broker.namespace == "historical"
        assert broker.ttl == 86400  # 24 hours in seconds

    def test_initialization_custom_ttl(self, mock_redis, mock_logger):
        """Test initialization with custom TTL"""
        broker = HistoricalMarketBroker(ttl=3600)

        assert broker.ttl == 3600

    def test_get_namespace_returns_historical(self, mock_redis, mock_logger):
        """Test _get_namespace returns correct namespace"""
        broker = HistoricalMarketBroker()

        assert broker._get_namespace() == "historical"

    def test_initialization_creates_logger(self, mock_redis, mock_logger):
        """Test initialization creates logger with class name"""
        broker = HistoricalMarketBroker()

        assert broker.logger is not None


class TestHistoricalMarketBrokerSetHistorical:
    """Test historical data storage"""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection"""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger"""
        with patch("system.algo_trader.redis.historical_market.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    @pytest.fixture
    def sample_candles_data(self):
        """Sample historical candles data"""
        return [
            {
                "datetime": 1609459200000,
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 104.0,
                "volume": 1000000,
            },
            {
                "datetime": 1609545600000,
                "open": 104.0,
                "high": 106.0,
                "low": 103.0,
                "close": 105.5,
                "volume": 1100000,
            },
        ]

    def test_set_historical_success(self, mock_redis, mock_logger, sample_candles_data):
        """Test successful historical data storage"""
        mock_redis["client"].set.return_value = True

        broker = HistoricalMarketBroker()
        result = broker.set_historical("AAPL", sample_candles_data)

        assert result is True
        mock_redis["client"].set.assert_called_once()

    def test_set_historical_uses_correct_key(self, mock_redis, mock_logger, sample_candles_data):
        """Test set_historical uses ticker as Redis key"""
        mock_redis["client"].set.return_value = True

        broker = HistoricalMarketBroker()
        broker.set_historical("TSLA", sample_candles_data)

        call_args = mock_redis["client"].set.call_args
        assert "historical:TSLA" in call_args[0]

    def test_set_historical_serializes_to_json(self, mock_redis, mock_logger, sample_candles_data):
        """Test historical data is serialized to JSON"""
        mock_redis["client"].set.return_value = True

        broker = HistoricalMarketBroker()
        broker.set_historical("AAPL", sample_candles_data)

        # Verify JSON serialization occurred
        call_args = mock_redis["client"].set.call_args
        stored_value = call_args[0][1]
        # Should be valid JSON string
        json.loads(stored_value)

    def test_set_historical_uses_default_ttl(self, mock_redis, mock_logger, sample_candles_data):
        """Test set_historical uses default TTL of 24 hours"""
        mock_redis["client"].set.return_value = True

        broker = HistoricalMarketBroker()
        broker.set_historical("AAPL", sample_candles_data)

        call_args = mock_redis["client"].set.call_args
        assert call_args[1]["ex"] == 86400

    def test_set_historical_uses_custom_ttl(self, mock_redis, mock_logger, sample_candles_data):
        """Test set_historical uses custom TTL"""
        mock_redis["client"].set.return_value = True

        broker = HistoricalMarketBroker(ttl=7200)
        broker.set_historical("AAPL", sample_candles_data)

        call_args = mock_redis["client"].set.call_args
        assert call_args[1]["ex"] == 7200

    def test_set_historical_logs_debug_on_success(
        self, mock_redis, mock_logger, sample_candles_data
    ):
        """Test successful storage logs debug message"""
        mock_redis["client"].set.return_value = True

        broker = HistoricalMarketBroker()
        broker.set_historical("AAPL", sample_candles_data)

        # Check debug was called with ticker
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("AAPL" in str(call) for call in debug_calls)

    def test_set_historical_failure(self, mock_redis, mock_logger, sample_candles_data):
        """Test historical data storage failure"""
        mock_redis["client"].set.return_value = False

        broker = HistoricalMarketBroker()
        result = broker.set_historical("AAPL", sample_candles_data)

        assert result is False

    def test_set_historical_empty_data(self, mock_redis, mock_logger):
        """Test storing empty historical data"""
        mock_redis["client"].set.return_value = True

        broker = HistoricalMarketBroker()
        result = broker.set_historical("AAPL", [])

        assert result is True


class TestHistoricalMarketBrokerGetHistorical:
    """Test historical data retrieval"""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection"""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger"""
        with patch("system.algo_trader.redis.historical_market.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_get_historical_success(self, mock_redis, mock_logger):
        """Test successful historical data retrieval"""
        stored_data = [
            {"datetime": 1609459200000, "close": 104.0},
            {"datetime": 1609545600000, "close": 105.5},
        ]
        mock_redis["client"].get.return_value = json.dumps(stored_data).encode("utf-8")

        broker = HistoricalMarketBroker()
        result = broker.get_historical("AAPL")

        assert result == stored_data
        assert isinstance(result, list)

    def test_get_historical_uses_correct_key(self, mock_redis, mock_logger):
        """Test get_historical uses correct Redis key"""
        mock_redis["client"].get.return_value = json.dumps([]).encode("utf-8")

        broker = HistoricalMarketBroker()
        broker.get_historical("TSLA")

        mock_redis["client"].get.assert_called_once_with("historical:TSLA")

    def test_get_historical_cache_miss_returns_empty_list(self, mock_redis, mock_logger):
        """Test cache miss returns empty list"""
        mock_redis["client"].get.return_value = None

        broker = HistoricalMarketBroker()
        result = broker.get_historical("MISSING")

        assert result == []

    def test_get_historical_cache_miss_logs_warning(self, mock_redis, mock_logger):
        """Test cache miss logs warning"""
        mock_redis["client"].get.return_value = None

        broker = HistoricalMarketBroker()
        broker.get_historical("MISSING")

        # Verify warning was logged
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any("MISSING" in str(call) for call in warning_calls)

    def test_get_historical_logs_debug(self, mock_redis, mock_logger):
        """Test get_historical logs debug message"""
        mock_redis["client"].get.return_value = json.dumps([]).encode("utf-8")

        broker = HistoricalMarketBroker()
        broker.get_historical("AAPL")

        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("AAPL" in str(call) for call in debug_calls)

    def test_get_historical_deserializes_json(self, mock_redis, mock_logger):
        """Test historical data is deserialized from JSON"""
        data = [{"key": "value"}]
        mock_redis["client"].get.return_value = json.dumps(data).encode("utf-8")

        broker = HistoricalMarketBroker()
        result = broker.get_historical("AAPL")

        assert result == data
        assert isinstance(result, list)


class TestHistoricalMarketBrokerMarketHours:
    """Test market hours operations"""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection"""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger"""
        with patch("system.algo_trader.redis.historical_market.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_set_market_hours_success(self, mock_redis, mock_logger):
        """Test successful market hours storage"""
        mock_redis["client"].hmset.return_value = True

        broker = HistoricalMarketBroker()
        market_hours = {"isOpen": "true", "sessionStart": "09:30", "sessionEnd": "16:00"}
        result = broker.set_market_hours(market_hours)

        assert result is True

    def test_set_market_hours_uses_correct_key(self, mock_redis, mock_logger):
        """Test set_market_hours uses 'hours' as key"""
        mock_redis["client"].hmset.return_value = True

        broker = HistoricalMarketBroker()
        broker.set_market_hours({"isOpen": "true"})

        call_args = mock_redis["client"].hmset.call_args
        assert "historical:hours" in call_args[0]

    def test_set_market_hours_ttl_12_hours(self, mock_redis, mock_logger):
        """Test market hours TTL is 12 hours (43200 seconds)"""
        mock_redis["client"].hmset.return_value = True

        broker = HistoricalMarketBroker()
        broker.set_market_hours({"isOpen": "true"})

        # Verify expire was called with 12 hours TTL
        mock_redis["client"].expire.assert_called_with("historical:hours", 43200)

    def test_get_market_hours_success(self, mock_redis, mock_logger):
        """Test successful market hours retrieval"""
        mock_redis["client"].hgetall.return_value = {b"isOpen": b"true", b"sessionStart": b"09:30"}

        broker = HistoricalMarketBroker()
        result = broker.get_market_hours()

        assert result == {"isOpen": "true", "sessionStart": "09:30"}

    def test_get_market_hours_cache_miss(self, mock_redis, mock_logger):
        """Test get_market_hours when no data exists"""
        mock_redis["client"].hgetall.return_value = {}

        broker = HistoricalMarketBroker()
        result = broker.get_market_hours()

        assert result == {}

    def test_get_market_hours_cache_miss_logs_warning(self, mock_redis, mock_logger):
        """Test cache miss logs warning"""
        mock_redis["client"].hgetall.return_value = {}

        broker = HistoricalMarketBroker()
        broker.get_market_hours()

        mock_logger.warning.assert_called_once_with("Cache miss: market_hours")


class TestHistoricalMarketBrokerIntegration:
    """Test integration scenarios"""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection"""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger"""
        with patch("system.algo_trader.redis.historical_market.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_store_and_retrieve_historical_data(self, mock_redis, mock_logger):
        """Test complete workflow: store then retrieve historical data"""
        test_data = [{"datetime": 1609459200000, "close": 104.0}]

        # Setup mocks
        mock_redis["client"].set.return_value = True
        mock_redis["client"].get.return_value = json.dumps(test_data).encode("utf-8")

        broker = HistoricalMarketBroker()

        # Store data
        assert broker.set_historical("AAPL", test_data) is True

        # Retrieve data
        result = broker.get_historical("AAPL")
        assert result == test_data

    def test_multiple_tickers_storage(self, mock_redis, mock_logger):
        """Test storing data for multiple tickers"""
        mock_redis["client"].set.return_value = True

        broker = HistoricalMarketBroker()

        tickers = ["AAPL", "TSLA", "GOOGL", "MSFT"]
        for ticker in tickers:
            data = [{"datetime": 1609459200000, "ticker": ticker}]
            assert broker.set_historical(ticker, data) is True

        assert mock_redis["client"].set.call_count == len(tickers)


class TestHistoricalMarketBrokerEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection"""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger"""
        with patch("system.algo_trader.redis.historical_market.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_ticker_with_special_characters(self, mock_redis, mock_logger):
        """Test ticker with special characters or unusual format"""
        mock_redis["client"].set.return_value = True
        mock_redis["client"].get.return_value = json.dumps([]).encode("utf-8")

        broker = HistoricalMarketBroker()

        unusual_tickers = ["BRK.B", "BF-A", "GOLD.TO", "^GSPC"]
        for ticker in unusual_tickers:
            assert broker.set_historical(ticker, []) is True
            assert broker.get_historical(ticker) == []

    def test_invalid_json_in_cache(self, mock_redis, mock_logger):
        """Test handling of corrupted JSON in cache"""
        mock_redis["client"].get.return_value = b"invalid json data"

        broker = HistoricalMarketBroker()
        result = broker.get_historical("AAPL")

        # Should return empty list when JSON is invalid (handled by base class)
        # The get_json method returns None on invalid JSON, which triggers the empty list return
        assert result == []
