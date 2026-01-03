"""Unit tests for WatchlistBroker - Watchlist Management.

Tests cover watchlist storage and retrieval using Redis sets.
All Redis operations are mocked to avoid requiring a Redis server.
"""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.redis.redis import BaseRedisClient
from system.algo_trader.redis.watchlist import WatchlistBroker


class TestWatchlistBrokerInitialization:
    """Test WatchlistBroker initialization."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.watchlist.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_initialization_default_ttl(self, mock_redis, mock_logger):
        """Test initialization with default TTL of None (no expiration)."""
        broker = WatchlistBroker()

        assert broker.namespace == "watchlist"
        assert broker.ttl is None

    def test_initialization_custom_ttl(self, mock_redis, mock_logger):
        """Test initialization with custom TTL."""
        broker = WatchlistBroker(ttl=3600)

        assert broker.ttl == 3600

    def test_get_namespace_returns_watchlist(self, mock_redis, mock_logger):
        """Test _get_namespace returns correct namespace."""
        broker = WatchlistBroker()

        assert broker._get_namespace() == "watchlist"

    def test_initialization_creates_logger(self, mock_redis, mock_logger):
        """Test initialization creates logger with class name."""
        broker = WatchlistBroker()

        assert broker.logger is not None

    def test_initialization_inherits_from_base_redis_client(self, mock_redis, mock_logger):
        """Test that WatchlistBroker inherits from BaseRedisClient."""
        broker = WatchlistBroker()

        assert isinstance(broker, BaseRedisClient)


class TestWatchlistBrokerSetWatchlist:
    """Test watchlist storage."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.watchlist.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_set_watchlist_success(self, mock_redis, mock_logger):
        """Test successful watchlist storage."""
        mock_redis["client"].sadd.return_value = 3

        broker = WatchlistBroker()
        tickers = ["AAPL", "TSLA", "GOOGL"]
        result = broker.set_watchlist(tickers)

        assert result == 3  # Number of tickers added

    def test_set_watchlist_default_strategy_all(self, mock_redis, mock_logger):
        """Test default strategy is 'all'."""
        mock_redis["client"].sadd.return_value = 1

        broker = WatchlistBroker()
        broker.set_watchlist(["AAPL"])

        # Should use 'all' as default strategy/key
        call_args = mock_redis["client"].sadd.call_args
        assert "watchlist:all" in call_args[0]

    def test_set_watchlist_custom_strategy(self, mock_redis, mock_logger):
        """Test setting watchlist with custom strategy name."""
        mock_redis["client"].sadd.return_value = 2

        broker = WatchlistBroker()
        tickers = ["AAPL", "MSFT"]
        result = broker.set_watchlist(tickers, strategy="tech_stocks")

        assert result == 2
        call_args = mock_redis["client"].sadd.call_args
        assert "watchlist:tech_stocks" in call_args[0]

    def test_set_watchlist_with_ttl(self, mock_redis, mock_logger):
        """Test setting watchlist with TTL."""
        mock_redis["client"].sadd.return_value = 1

        broker = WatchlistBroker(ttl=86400)
        broker.set_watchlist(["AAPL"])

        # Verify TTL was applied
        mock_redis["client"].expire.assert_called()

    def test_set_watchlist_without_ttl(self, mock_redis, mock_logger):
        """Test setting watchlist without TTL (persistent)."""
        mock_redis["client"].sadd.return_value = 1

        broker = WatchlistBroker(ttl=None)
        broker.set_watchlist(["AAPL"])

        # No expire call when TTL is None
        # Note: sadd is called with ttl=None

    def test_set_watchlist_single_ticker(self, mock_redis, mock_logger):
        """Test adding single ticker to watchlist."""
        mock_redis["client"].sadd.return_value = 1

        broker = WatchlistBroker()
        result = broker.set_watchlist(["AAPL"])

        assert result == 1

    def test_set_watchlist_multiple_tickers(self, mock_redis, mock_logger):
        """Test adding multiple tickers to watchlist."""
        mock_redis["client"].sadd.return_value = 5

        broker = WatchlistBroker()
        tickers = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"]
        result = broker.set_watchlist(tickers)

        assert result == 5

    def test_set_watchlist_duplicate_tickers(self, mock_redis, mock_logger):
        """Test adding duplicate tickers (Redis set handles duplicates)."""
        mock_redis["client"].sadd.return_value = 1  # Only 1 unique added

        broker = WatchlistBroker()
        tickers = ["AAPL", "AAPL", "AAPL"]
        result = broker.set_watchlist(tickers)

        assert result == 1

    def test_set_watchlist_empty_list(self, mock_redis, mock_logger):
        """Test setting watchlist with empty ticker list."""
        mock_redis["client"].sadd.return_value = 0

        broker = WatchlistBroker()
        result = broker.set_watchlist([])

        assert result == 0


class TestWatchlistBrokerGetWatchlist:
    """Test watchlist retrieval."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.watchlist.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_get_watchlist_success(self, mock_redis, mock_logger):
        """Test successful watchlist retrieval."""
        mock_redis["client"].smembers.return_value = {b"AAPL", b"TSLA", b"GOOGL"}

        broker = WatchlistBroker()
        result = broker.get_watchlist()

        assert result == {"AAPL", "TSLA", "GOOGL"}
        assert isinstance(result, set)

    def test_get_watchlist_default_strategy_all(self, mock_redis, mock_logger):
        """Test get_watchlist uses default strategy 'all'."""
        mock_redis["client"].smembers.return_value = set()

        broker = WatchlistBroker()
        broker.get_watchlist()

        call_args = mock_redis["client"].smembers.call_args
        assert "watchlist:all" in call_args[0]

    def test_get_watchlist_custom_strategy(self, mock_redis, mock_logger):
        """Test getting watchlist with custom strategy."""
        mock_redis["client"].smembers.return_value = {b"AAPL", b"MSFT"}

        broker = WatchlistBroker()
        result = broker.get_watchlist(strategy="tech_stocks")

        assert result == {"AAPL", "MSFT"}
        call_args = mock_redis["client"].smembers.call_args
        assert "watchlist:tech_stocks" in call_args[0]

    def test_get_watchlist_empty(self, mock_redis, mock_logger):
        """Test get_watchlist when no tickers exist."""
        mock_redis["client"].smembers.return_value = set()

        broker = WatchlistBroker()
        result = broker.get_watchlist()

        assert result == set()
        assert isinstance(result, set)

    def test_get_watchlist_logs_info(self, mock_redis, mock_logger):
        """Test get_watchlist logs info message with watchlist."""
        mock_redis["client"].smembers.return_value = {b"AAPL", b"TSLA"}

        broker = WatchlistBroker()
        broker.get_watchlist()

        # Should log the current watchlist
        mock_logger.info.assert_called()
        info_call = str(mock_logger.info.call_args)
        assert "watchlist" in info_call.lower()

    def test_get_watchlist_single_ticker(self, mock_redis, mock_logger):
        """Test getting watchlist with single ticker."""
        mock_redis["client"].smembers.return_value = {b"AAPL"}

        broker = WatchlistBroker()
        result = broker.get_watchlist()

        assert result == {"AAPL"}

    def test_get_watchlist_many_tickers(self, mock_redis, mock_logger):
        """Test getting large watchlist."""
        tickers = {f"TICK{i}".encode() for i in range(100)}
        mock_redis["client"].smembers.return_value = tickers

        broker = WatchlistBroker()
        result = broker.get_watchlist()

        assert len(result) == 100


class TestWatchlistBrokerIntegration:
    """Test integration scenarios."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.watchlist.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_add_and_retrieve_watchlist(self, mock_redis, mock_logger):
        """Test complete workflow: add tickers then retrieve."""
        tickers = {"AAPL", "TSLA", "GOOGL"}

        # Setup mocks
        mock_redis["client"].sadd.return_value = 3
        mock_redis["client"].smembers.return_value = {t.encode() for t in tickers}

        broker = WatchlistBroker()

        # Add to watchlist
        add_result = broker.set_watchlist(list(tickers))
        assert add_result == 3

        # Retrieve watchlist
        get_result = broker.get_watchlist()
        assert get_result == tickers

    def test_multiple_strategies(self, mock_redis, mock_logger):
        """Test using multiple strategy watchlists."""
        mock_redis["client"].sadd.return_value = 2
        mock_redis["client"].smembers.side_effect = [
            {b"AAPL", b"MSFT"},  # tech_stocks
            {b"JPM", b"BAC"},  # finance_stocks
        ]

        broker = WatchlistBroker()

        # Add tech stocks
        broker.set_watchlist(["AAPL", "MSFT"], strategy="tech_stocks")

        # Add finance stocks
        broker.set_watchlist(["JPM", "BAC"], strategy="finance_stocks")

        # Retrieve each strategy
        tech = broker.get_watchlist(strategy="tech_stocks")
        finance = broker.get_watchlist(strategy="finance_stocks")

        assert tech == {"AAPL", "MSFT"}
        assert finance == {"JPM", "BAC"}

    def test_incremental_watchlist_updates(self, mock_redis, mock_logger):
        """Test adding tickers incrementally to same watchlist."""
        mock_redis["client"].sadd.side_effect = [2, 2, 1]  # Add different amounts

        broker = WatchlistBroker()

        # First batch
        broker.set_watchlist(["AAPL", "TSLA"])

        # Second batch
        broker.set_watchlist(["GOOGL", "MSFT"])

        # Third batch (with duplicate)
        broker.set_watchlist(["AMZN"])

        # All three calls should succeed
        assert mock_redis["client"].sadd.call_count == 3

    def test_watchlist_persistence_with_ttl(self, mock_redis, mock_logger):
        """Test watchlist with TTL expiration."""
        mock_redis["client"].sadd.return_value = 1
        mock_redis["client"].smembers.side_effect = [
            {b"AAPL"},  # First call: data exists
            set(),  # Second call: data expired
        ]

        broker = WatchlistBroker(ttl=60)

        # Add watchlist
        broker.set_watchlist(["AAPL"])

        # Retrieve immediately (exists)
        result1 = broker.get_watchlist()
        assert result1 == {"AAPL"}

        # Retrieve after expiry (empty)
        result2 = broker.get_watchlist()
        assert result2 == set()


class TestWatchlistBrokerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.watchlist.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_tickers_with_special_characters(self, mock_redis, mock_logger):
        """Test tickers with special characters."""
        mock_redis["client"].sadd.return_value = 3
        mock_redis["client"].smembers.return_value = {b"BRK.B", b"BF-A", b"^GSPC"}

        broker = WatchlistBroker()

        # Add tickers with special chars
        result = broker.set_watchlist(["BRK.B", "BF-A", "^GSPC"])
        assert result == 3

        # Retrieve them
        watchlist = broker.get_watchlist()
        assert "BRK.B" in watchlist
        assert "BF-A" in watchlist
        assert "^GSPC" in watchlist

    def test_very_long_strategy_name(self, mock_redis, mock_logger):
        """Test strategy with very long name."""
        mock_redis["client"].sadd.return_value = 1

        broker = WatchlistBroker()
        long_strategy = "a" * 1000

        result = broker.set_watchlist(["AAPL"], strategy=long_strategy)
        assert result == 1

    def test_strategy_with_special_characters(self, mock_redis, mock_logger):
        """Test strategy name with special characters."""
        mock_redis["client"].sadd.return_value = 1

        broker = WatchlistBroker()
        special_strategy = "tech-stocks_2024!@#"

        result = broker.set_watchlist(["AAPL"], strategy=special_strategy)
        assert result == 1

    def test_unicode_ticker_symbols(self, mock_redis, mock_logger):
        """Test unicode characters in ticker symbols."""
        mock_redis["client"].sadd.return_value = 1

        broker = WatchlistBroker()

        # Some international tickers might have unicode
        result = broker.set_watchlist(["票号"])
        assert result == 1

    def test_set_watchlist_redis_error(self, mock_redis, mock_logger):
        """Test set_watchlist handles Redis errors."""
        mock_redis["client"].sadd.side_effect = Exception("Redis error")

        broker = WatchlistBroker()

        # Should handle exception and return 0
        result = broker.set_watchlist(["AAPL"])
        assert result == 0

    def test_get_watchlist_redis_error(self, mock_redis, mock_logger):
        """Test get_watchlist handles Redis errors."""
        mock_redis["client"].smembers.side_effect = Exception("Redis error")

        broker = WatchlistBroker()

        # Should handle exception and return empty set
        result = broker.get_watchlist()
        assert result == set()

    def test_case_sensitivity(self, mock_redis, mock_logger):
        """Test that ticker symbols maintain case sensitivity."""
        mock_redis["client"].sadd.return_value = 2
        mock_redis["client"].smembers.return_value = {b"aapl", b"AAPL"}

        broker = WatchlistBroker()

        # Add both lowercase and uppercase
        broker.set_watchlist(["aapl", "AAPL"])

        # Should maintain both
        result = broker.get_watchlist()
        assert "aapl" in result
        assert "AAPL" in result

    def test_very_large_watchlist(self, mock_redis, mock_logger):
        """Test watchlist with thousands of tickers."""
        mock_redis["client"].sadd.return_value = 1000

        broker = WatchlistBroker()
        large_watchlist = [f"TICKER{i}" for i in range(1000)]

        result = broker.set_watchlist(large_watchlist)
        assert result == 1000
