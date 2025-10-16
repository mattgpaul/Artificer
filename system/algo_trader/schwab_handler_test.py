"""Unit and integration tests for SchwabHandler."""
import pytest
from unittest.mock import MagicMock, patch, call
from system.algo_trader.schwab_handler import SchwabHandler
from system.algo_trader.redis_client import AlgoTraderRedisClient


@pytest.mark.unit
class TestSchwabHandlerUnit:
    """Unit tests for SchwabHandler with mocking."""
    
    @patch('infrastructure.clients.redis_client.redis.ConnectionPool')
    @patch('infrastructure.clients.redis_client.redis.Redis')
    def test_init(self, mock_redis, mock_pool):
        """Test SchwabHandler initialization."""
        redis_client = AlgoTraderRedisClient()
        handler = SchwabHandler(redis_client)
        
        assert handler.redis == redis_client
        assert handler.schwab_client is not None
        assert handler.base_url == "https://api.schwabapi.com"
    
    @patch('infrastructure.clients.redis_client.redis.ConnectionPool')
    @patch('infrastructure.clients.redis_client.redis.Redis')
    @patch('builtins.input')
    def test_authenticate_success(self, mock_input, mock_redis, mock_pool):
        """Test successful authentication flow."""
        redis_client = AlgoTraderRedisClient()
        mock_redis_instance = MagicMock()
        mock_redis_instance.set.return_value = True
        redis_client.client = mock_redis_instance
        
        handler = SchwabHandler(redis_client)
        
        # Mock user input for the redirect URL
        mock_input.return_value = "https://127.0.0.1?code=test_code%40&session=xyz"
        
        # Mock the schwab client methods
        mock_schwab = MagicMock()
        mock_schwab.get_authorization_url.return_value = "https://auth.schwab.com/..."
        mock_schwab.get_tokens_from_code.return_value = {
            'access_token': 'test_access',
            'refresh_token': 'test_refresh',
            'expires_in': 1800
        }
        handler.schwab_client = mock_schwab
        
        result = handler.authenticate()
        
        assert result is True
        mock_schwab.get_authorization_url.assert_called_once()
        mock_schwab.get_tokens_from_code.assert_called_once_with("test_code@", handler.redirect_uri)
    
    @patch('infrastructure.clients.redis_client.redis.ConnectionPool')
    @patch('infrastructure.clients.redis_client.redis.Redis')
    def test_get_valid_token_exists(self, mock_redis, mock_pool):
        """Test getting valid token when it exists in Redis."""
        redis_client = AlgoTraderRedisClient()
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = b"existing_token"
        redis_client.client = mock_redis_instance
        
        handler = SchwabHandler(redis_client)
        token = handler._get_valid_token()
        
        assert token == "existing_token"
    
    @patch('infrastructure.clients.redis_client.redis.ConnectionPool')
    @patch('infrastructure.clients.redis_client.redis.Redis')
    def test_refresh_token_success(self, mock_redis, mock_pool):
        """Test successful token refresh."""
        redis_client = AlgoTraderRedisClient()
        mock_redis_instance = MagicMock()
        mock_redis_instance.set.return_value = True
        redis_client.client = mock_redis_instance
        
        handler = SchwabHandler(redis_client)
        
        # Mock the schwab client refresh method
        mock_schwab = MagicMock()
        mock_schwab.refresh_access_token.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 1800
        }
        handler.schwab_client = mock_schwab
        
        token = handler._refresh_token("old_refresh_token")
        
        assert token == "new_access_token"
        mock_schwab.refresh_access_token.assert_called_once_with("old_refresh_token")
    
    @patch('infrastructure.clients.redis_client.redis.ConnectionPool')
    @patch('infrastructure.clients.redis_client.redis.Redis')
    def test_refresh_token_failure(self, mock_redis, mock_pool):
        """Test token refresh failure."""
        redis_client = AlgoTraderRedisClient()
        handler = SchwabHandler(redis_client)
        
        # Mock the schwab client refresh method to raise an exception
        mock_schwab = MagicMock()
        mock_schwab.refresh_access_token.side_effect = Exception("Token refresh failed: 401 - Unauthorized")
        handler.schwab_client = mock_schwab
        
        token = handler._refresh_token("invalid_refresh_token")
        
        assert token is None
    
    @patch('infrastructure.clients.redis_client.redis.ConnectionPool')
    @patch('infrastructure.clients.redis_client.redis.Redis')
    @patch('system.algo_trader.schwab_handler.requests.get')
    def test_get_price_history_success(self, mock_get, mock_redis, mock_pool):
        """Test successful price history retrieval."""
        redis_client = AlgoTraderRedisClient()
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = b"valid_token"
        redis_client.client = mock_redis_instance
        
        handler = SchwabHandler(redis_client)
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbol': 'AAPL',
            'candles': [
                {'open': 150.0, 'high': 152.0, 'low': 149.0, 'close': 151.0, 'volume': 1000000}
            ]
        }
        mock_get.return_value = mock_response
        
        data = handler.get_price_history("AAPL")
        
        assert data is not None
        assert data['symbol'] == 'AAPL'
        assert len(data['candles']) == 1
        mock_get.assert_called_once()
    
    @patch('infrastructure.clients.redis_client.redis.ConnectionPool')
    @patch('infrastructure.clients.redis_client.redis.Redis')
    def test_get_price_history_no_token(self, mock_redis, mock_pool):
        """Test price history when no valid token available."""
        redis_client = AlgoTraderRedisClient()
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = None
        redis_client.client = mock_redis_instance
        
        handler = SchwabHandler(redis_client)
        data = handler.get_price_history("AAPL")
        
        assert data is None


@pytest.mark.integration
class TestSchwabHandlerIntegration:
    """
    Integration tests for SchwabHandler.
    
    These tests require:
    - Redis instance running
    - Valid Schwab API credentials in environment
    - Network access to Schwab API
    
    Note: These tests may fail if authentication is not set up.
    Run unit tests for basic functionality verification.
    """
    
    def test_redis_connection(self):
        """Test that Redis client can connect."""
        redis_client = AlgoTraderRedisClient()
        result = redis_client.ping()
        assert result is True
    
    def test_token_storage_retrieval(self):
        """Test storing and retrieving tokens from Redis."""
        redis_client = AlgoTraderRedisClient()
        
        # Store tokens
        assert redis_client.store_access_token("test_access", ttl=60)
        assert redis_client.store_refresh_token("test_refresh")
        
        # Retrieve tokens
        access = redis_client.get_access_token()
        refresh = redis_client.get_refresh_token()
        
        assert access == "test_access"
        assert refresh == "test_refresh"
        
        # Cleanup
        redis_client.delete("schwab_access_token")
        redis_client.delete("schwab_refresh_token")

