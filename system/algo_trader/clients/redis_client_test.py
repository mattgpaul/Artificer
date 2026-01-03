"""Unit tests for AlgoTraderRedisClient."""

from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.clients.redis_client import AlgoTraderRedisClient


@pytest.mark.unit
class TestAlgoTraderRedisClient:
    """Unit tests for AlgoTraderRedisClient."""

    @patch("infrastructure.clients.redis_client.redis.ConnectionPool")
    @patch("infrastructure.clients.redis_client.redis.Redis")
    def test_namespace(self, mock_redis, mock_pool):
        """Test that namespace is correctly set to 'algo_trader'."""
        client = AlgoTraderRedisClient()
        assert client.namespace == "algo_trader"

    @patch("infrastructure.clients.redis_client.redis.ConnectionPool")
    @patch("infrastructure.clients.redis_client.redis.Redis")
    def test_store_access_token(self, mock_redis, mock_pool):
        """Test storing access token with TTL."""
        client = AlgoTraderRedisClient()
        mock_client = MagicMock()
        mock_client.set.return_value = True
        client.client = mock_client

        result = client.store_access_token("test_token", ttl=1800)

        assert result is True
        mock_client.set.assert_called_once_with(
            "algo_trader:schwab_access_token", "test_token", ex=1800
        )

    @patch("infrastructure.clients.redis_client.redis.ConnectionPool")
    @patch("infrastructure.clients.redis_client.redis.Redis")
    def test_get_access_token(self, mock_redis, mock_pool):
        """Test retrieving access token."""
        client = AlgoTraderRedisClient()
        mock_client = MagicMock()
        mock_client.get.return_value = b"test_token"
        client.client = mock_client

        token = client.get_access_token()

        assert token == "test_token"
        mock_client.get.assert_called_once_with("algo_trader:schwab_access_token")

    @patch("infrastructure.clients.redis_client.redis.ConnectionPool")
    @patch("infrastructure.clients.redis_client.redis.Redis")
    def test_store_refresh_token(self, mock_redis, mock_pool):
        """Test storing refresh token without expiration."""
        client = AlgoTraderRedisClient()
        mock_client = MagicMock()
        mock_client.set.return_value = True
        client.client = mock_client

        result = client.store_refresh_token("refresh_token")

        assert result is True
        mock_client.set.assert_called_once_with(
            "algo_trader:schwab_refresh_token", "refresh_token", ex=None
        )

    @patch("infrastructure.clients.redis_client.redis.ConnectionPool")
    @patch("infrastructure.clients.redis_client.redis.Redis")
    def test_get_refresh_token(self, mock_redis, mock_pool):
        """Test retrieving refresh token."""
        client = AlgoTraderRedisClient()
        mock_client = MagicMock()
        mock_client.get.return_value = b"refresh_token"
        client.client = mock_client

        token = client.get_refresh_token()

        assert token == "refresh_token"
        mock_client.get.assert_called_once_with("algo_trader:schwab_refresh_token")

    @patch("infrastructure.clients.redis_client.redis.ConnectionPool")
    @patch("infrastructure.clients.redis_client.redis.Redis")
    def test_get_token_not_found(self, mock_redis, mock_pool):
        """Test retrieving token when it doesn't exist."""
        client = AlgoTraderRedisClient()
        mock_client = MagicMock()
        mock_client.get.return_value = None
        client.client = mock_client

        token = client.get_access_token()

        assert token is None
