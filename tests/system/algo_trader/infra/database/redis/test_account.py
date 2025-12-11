"""Unit tests for AccountBroker - Account Token Management.

Tests cover token storage and retrieval for OAuth2 authentication.
All Redis operations are mocked to avoid requiring a Redis server.
"""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.redis.base_redis_client import BaseRedisClient
from system.algo_trader.redis.account import AccountBroker


class TestAccountBrokerInitialization:
    """Test AccountBroker initialization."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.base_redis_client.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.account.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_initialization_success(self, mock_redis, mock_logger):
        """Test successful AccountBroker initialization."""
        broker = AccountBroker()

        assert broker.namespace == "account"
        assert broker.logger is not None

    def test_initialization_inherits_from_base_redis_client(self, mock_redis, mock_logger):
        """Test that AccountBroker inherits from BaseRedisClient."""
        broker = AccountBroker()

        assert isinstance(broker, BaseRedisClient)

    def test_get_namespace_returns_account(self, mock_redis, mock_logger):
        """Test _get_namespace returns correct namespace."""
        broker = AccountBroker()

        assert broker._get_namespace() == "account"

    def test_initialization_creates_connection_pool(self, mock_redis, mock_logger):
        """Test initialization creates Redis connection pool."""
        AccountBroker()

        mock_redis["module"].ConnectionPool.assert_called()
        mock_redis["module"].Redis.assert_called()


class TestAccountBrokerRefreshToken:
    """Test refresh token operations."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.base_redis_client.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.account.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_set_refresh_token_success(self, mock_redis, mock_logger):
        """Test successful refresh token storage."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        result = broker.set_refresh_token("test_refresh_token_12345")

        assert result is True
        # Verify correct TTL (90 days in seconds)
        expected_ttl = 90 * 24 * 60
        mock_redis["client"].set.assert_called_once()
        call_args = mock_redis["client"].set.call_args
        assert call_args[1]["ex"] == expected_ttl

    def test_set_refresh_token_uses_correct_key(self, mock_redis, mock_logger):
        """Test set_refresh_token uses correct Redis key."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        broker.set_refresh_token("test_token")

        call_args = mock_redis["client"].set.call_args
        assert "account:refresh-token" in call_args[0]

    def test_set_refresh_token_ttl_is_90_days(self, mock_redis, mock_logger):
        """Test refresh token TTL is exactly 90 days."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        broker.set_refresh_token("test_token")

        expected_ttl = 90 * 24 * 60  # 129,600 seconds
        call_args = mock_redis["client"].set.call_args
        assert call_args[1]["ex"] == expected_ttl

    def test_set_refresh_token_failure(self, mock_redis, mock_logger):
        """Test refresh token storage failure."""
        mock_redis["client"].set.return_value = False

        broker = AccountBroker()
        result = broker.set_refresh_token("test_token")

        assert result is False

    def test_get_refresh_token_success(self, mock_redis, mock_logger):
        """Test successful refresh token retrieval."""
        mock_redis["client"].get.return_value = b"stored_refresh_token"

        broker = AccountBroker()
        result = broker.get_refresh_token()

        assert result == "stored_refresh_token"
        mock_redis["client"].get.assert_called_once_with("account:refresh-token")

    def test_get_refresh_token_not_found(self, mock_redis, mock_logger):
        """Test refresh token retrieval when token doesn't exist."""
        mock_redis["client"].get.return_value = None

        broker = AccountBroker()
        result = broker.get_refresh_token()

        assert result is None

    def test_get_refresh_token_uses_correct_key(self, mock_redis, mock_logger):
        """Test get_refresh_token uses correct Redis key."""
        mock_redis["client"].get.return_value = b"token"

        broker = AccountBroker()
        broker.get_refresh_token()

        mock_redis["client"].get.assert_called_once_with("account:refresh-token")


class TestAccountBrokerAccessToken:
    """Test access token operations."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.base_redis_client.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.account.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_set_access_token_success(self, mock_redis, mock_logger):
        """Test successful access token storage."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        result = broker.set_access_token("test_access_token_67890")

        assert result is True

    def test_set_access_token_default_ttl(self, mock_redis, mock_logger):
        """Test access token uses default TTL of 30 minutes."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        broker.set_access_token("test_token")

        # Default TTL should be 30 minutes = 1800 seconds
        expected_ttl = 30 * 60
        call_args = mock_redis["client"].set.call_args
        assert call_args[1]["ex"] == expected_ttl

    def test_set_access_token_custom_ttl(self, mock_redis, mock_logger):
        """Test access token with custom TTL."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        broker.set_access_token("test_token", ttl=60)

        # Custom TTL of 60 seconds
        expected_ttl = 60
        call_args = mock_redis["client"].set.call_args
        assert call_args[1]["ex"] == expected_ttl

    def test_set_access_token_uses_correct_key(self, mock_redis, mock_logger):
        """Test set_access_token uses correct Redis key."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        broker.set_access_token("test_token")

        call_args = mock_redis["client"].set.call_args
        assert "account:access-token" in call_args[0]

    def test_set_access_token_failure(self, mock_redis, mock_logger):
        """Test access token storage failure."""
        mock_redis["client"].set.return_value = False

        broker = AccountBroker()
        result = broker.set_access_token("test_token")

        assert result is False

    def test_get_access_token_success(self, mock_redis, mock_logger):
        """Test successful access token retrieval."""
        mock_redis["client"].get.return_value = b"stored_access_token"

        broker = AccountBroker()
        result = broker.get_access_token()

        assert result == "stored_access_token"
        mock_redis["client"].get.assert_called_once_with("account:access-token")

    def test_get_access_token_not_found(self, mock_redis, mock_logger):
        """Test access token retrieval when token doesn't exist."""
        mock_redis["client"].get.return_value = None

        broker = AccountBroker()
        result = broker.get_access_token()

        assert result is None

    def test_get_access_token_expired(self, mock_redis, mock_logger):
        """Test access token retrieval when token has expired."""
        mock_redis["client"].get.return_value = None  # Expired tokens return None

        broker = AccountBroker()
        result = broker.get_access_token()

        assert result is None


class TestAccountBrokerIntegration:
    """Test integration scenarios with multiple operations."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.base_redis_client.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.account.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_oauth_token_lifecycle(self, mock_redis, mock_logger):
        """Test complete OAuth token lifecycle."""
        mock_redis["client"].set.return_value = True
        mock_redis["client"].get.side_effect = [b"refresh_token_value", b"access_token_value"]

        broker = AccountBroker()

        # Store tokens
        assert broker.set_refresh_token("refresh_token_value") is True
        assert broker.set_access_token("access_token_value") is True

        # Retrieve tokens
        refresh_token = broker.get_refresh_token()
        access_token = broker.get_access_token()

        assert refresh_token == "refresh_token_value"
        assert access_token == "access_token_value"

    def test_token_refresh_workflow(self, mock_redis, mock_logger):
        """Test token refresh workflow: get refresh token -> set new access token."""
        mock_redis["client"].get.return_value = b"valid_refresh_token"
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()

        # Get refresh token for renewal
        refresh_token = broker.get_refresh_token()
        assert refresh_token == "valid_refresh_token"

        # Set new access token after refresh
        assert broker.set_access_token("new_access_token") is True

    def test_expired_access_token_with_valid_refresh(self, mock_redis, mock_logger):
        """Test scenario where access token expired but refresh token valid."""
        mock_redis["client"].get.side_effect = [
            None,  # Access token expired
            b"valid_refresh_token",  # Refresh token still valid
        ]
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()

        # Access token expired
        access_token = broker.get_access_token()
        assert access_token is None

        # Refresh token still valid
        refresh_token = broker.get_refresh_token()
        assert refresh_token == "valid_refresh_token"

        # Can set new access token
        assert broker.set_access_token("refreshed_access_token") is True

    def test_both_tokens_expired(self, mock_redis, mock_logger):
        """Test scenario where both tokens are expired."""
        mock_redis["client"].get.return_value = None

        broker = AccountBroker()

        # Both tokens expired
        assert broker.get_access_token() is None
        assert broker.get_refresh_token() is None

    def test_update_existing_tokens(self, mock_redis, mock_logger):
        """Test updating existing tokens with new values."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()

        # Set initial tokens
        assert broker.set_refresh_token("initial_refresh") is True
        assert broker.set_access_token("initial_access") is True

        # Update with new tokens
        assert broker.set_refresh_token("updated_refresh") is True
        assert broker.set_access_token("updated_access") is True

        assert mock_redis["client"].set.call_count == 4


class TestAccountBrokerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.base_redis_client.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("system.algo_trader.redis.account.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_set_empty_string_token(self, mock_redis, mock_logger):
        """Test storing empty string as token."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        result = broker.set_access_token("")

        assert result is True

    def test_set_very_long_token(self, mock_redis, mock_logger):
        """Test storing very long token string."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        long_token = "x" * 10000
        result = broker.set_refresh_token(long_token)

        assert result is True

    def test_set_token_with_special_characters(self, mock_redis, mock_logger):
        """Test storing token with special characters."""
        mock_redis["client"].set.return_value = True

        broker = AccountBroker()
        special_token = "token!@#$%^&*()_+-={}[]|:\";'<>?,./~`"
        result = broker.set_access_token(special_token)

        assert result is True

    def test_redis_connection_error_on_set(self, mock_redis, mock_logger):
        """Test handling Redis connection error during set."""
        mock_redis["client"].set.side_effect = Exception("Connection error")

        broker = AccountBroker()

        # BaseRedisClient should handle exception and return False
        result = broker.set_access_token("test_token")

        # Error should be logged but not raised
        assert result is False

    def test_redis_connection_error_on_get(self, mock_redis, mock_logger):
        """Test handling Redis connection error during get."""
        mock_redis["client"].get.side_effect = Exception("Connection error")

        broker = AccountBroker()

        # BaseRedisClient should handle exception and return None
        result = broker.get_access_token()

        assert result is None
