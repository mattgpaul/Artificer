"""
Unit tests for SchwabClient - OAuth2 and Token Management

Tests cover token lifecycle, OAuth2 flow, and error handling scenarios.
All external dependencies are mocked to avoid network calls.
"""

import os
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta

from system.algo_trader.schwab.schwab_client import SchwabClient


class TestSchwabClientInitialization:
    """Test SchwabClient initialization and configuration validation"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict(os.environ, {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.schwab_client.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker
            }

    def test_initialization_success(self, mock_dependencies):
        """Test successful SchwabClient initialization"""
        client = SchwabClient()
        
        assert client.api_key == 'test_api_key'
        assert client.secret == 'test_secret'
        assert client.app_name == 'test_app_name'
        assert client.base_url == "https://api.schwabapi.com"
        assert client.account_broker is not None

    def test_initialization_missing_env_vars(self):
        """Test initialization fails with missing environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required Schwab environment variables"):
                SchwabClient()

    def test_initialization_partial_env_vars(self):
        """Test initialization fails with partial environment variables"""
        with patch.dict(os.environ, {
            'SCHWAB_API_KEY': 'test_key',
            # Missing SCHWAB_SECRET and SCHWAB_APP_NAME
        }):
            with pytest.raises(ValueError, match="Missing required Schwab environment variables"):
                SchwabClient()


class TestSchwabClientTokenManagement:
    """Test token lifecycle and refresh functionality"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict(os.environ, {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.schwab_client.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class, \
             patch('system.algo_trader.schwab.schwab_client.requests') as mock_requests:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker,
                'requests': mock_requests
            }

    def test_get_valid_access_token_from_redis(self, mock_dependencies):
        """Test getting valid access token from Redis"""
        mock_dependencies['broker'].get_access_token.return_value = 'valid_token'
        
        client = SchwabClient()
        token = client.get_valid_access_token()
        
        assert token == 'valid_token'
        mock_dependencies['broker'].get_access_token.assert_called_once()

    def test_refresh_token_from_redis_success(self, mock_dependencies):
        """Test successful token refresh using Redis refresh token"""
        # Setup mocks
        mock_dependencies['broker'].get_access_token.return_value = None  # No access token
        mock_dependencies['broker'].get_refresh_token.return_value = 'refresh_token'
        
        # Mock successful refresh response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token'
        }
        mock_dependencies['requests'].post.return_value = mock_response
        
        client = SchwabClient()
        result = client._refresh_access_token_from_redis()
        
        assert result is True
        mock_dependencies['broker'].set_access_token.assert_called_with('new_access_token')
        mock_dependencies['broker'].set_refresh_token.assert_called_with('new_refresh_token')

    def test_refresh_token_from_redis_no_refresh_token(self, mock_dependencies):
        """Test refresh fails when no refresh token in Redis"""
        mock_dependencies['broker'].get_access_token.return_value = None
        mock_dependencies['broker'].get_refresh_token.return_value = None
        
        client = SchwabClient()
        result = client._refresh_access_token_from_redis()
        
        assert result is False

    def test_refresh_token_from_redis_api_failure(self, mock_dependencies):
        """Test refresh fails when API returns error"""
        mock_dependencies['broker'].get_access_token.return_value = None
        mock_dependencies['broker'].get_refresh_token.return_value = 'refresh_token'
        
        # Mock failed refresh response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_dependencies['requests'].post.return_value = mock_response
        
        client = SchwabClient()
        result = client._refresh_access_token_from_redis()
        
        assert result is False

    def test_load_refresh_token_from_env_success(self, mock_dependencies):
        """Test loading refresh token from environment variables"""
        with patch.dict(os.environ, {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name',
            'SCHWAB_REFRESH_TOKEN': 'env_refresh_token'
        }):
            client = SchwabClient()
            result = client._load_refresh_token_from_env()
            
            assert result is True
            mock_dependencies['broker'].set_refresh_token.assert_called_with('env_refresh_token')

    def test_load_refresh_token_from_env_missing(self, mock_dependencies):
        """Test loading refresh token fails when not in environment"""
        client = SchwabClient()
        result = client._load_refresh_token_from_env()
        
        assert result is False

    def test_make_refresh_request_success(self, mock_dependencies):
        """Test successful refresh request"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token'
        }
        mock_dependencies['requests'].post.return_value = mock_response
        
        client = SchwabClient()
        result = client._make_refresh_request('refresh_token')
        
        assert result is not None
        assert result['access_token'] == 'new_access_token'
        assert result['refresh_token'] == 'new_refresh_token'

    def test_make_refresh_request_keeps_original_refresh_token(self, mock_dependencies):
        """Test refresh request keeps original refresh token when not provided"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token'
            # No refresh_token in response
        }
        mock_dependencies['requests'].post.return_value = mock_response
        
        client = SchwabClient()
        result = client._make_refresh_request('original_refresh_token')
        
        assert result['access_token'] == 'new_access_token'
        assert result['refresh_token'] == 'original_refresh_token'


class TestSchwabClientOAuth2Flow:
    """Test OAuth2 authentication flow"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict(os.environ, {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.schwab_client.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class, \
             patch('system.algo_trader.schwab.schwab_client.requests') as mock_requests, \
             patch('builtins.input') as mock_input, \
             patch('builtins.print') as mock_print:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker,
                'requests': mock_requests,
                'input': mock_input,
                'print': mock_print
            }

    def test_perform_oauth2_flow_success(self, mock_dependencies):
        """Test successful OAuth2 flow"""
        # Mock user input
        mock_dependencies['input'].return_value = 'https://127.0.0.1/?code=test_code%40'
        
        # Mock successful token exchange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'oauth_access_token',
            'refresh_token': 'oauth_refresh_token'
        }
        mock_dependencies['requests'].post.return_value = mock_response
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data='export SCHWAB_API_KEY=test_api_key\n')):
            client = SchwabClient()
            result = client._perform_oauth2_flow()
        
        assert result is not None
        assert result['access_token'] == 'oauth_access_token'
        assert result['refresh_token'] == 'oauth_refresh_token'
        
        # Verify tokens were stored
        mock_dependencies['broker'].set_access_token.assert_called_with('oauth_access_token')
        mock_dependencies['broker'].set_refresh_token.assert_called_with('oauth_refresh_token')

    def test_perform_oauth2_flow_invalid_url(self, mock_dependencies):
        """Test OAuth2 flow fails with invalid redirect URL"""
        mock_dependencies['input'].return_value = 'invalid_url'
        
        client = SchwabClient()
        result = client._perform_oauth2_flow()
        
        assert result is None

    def test_exchange_code_for_tokens_success(self, mock_dependencies):
        """Test successful code exchange for tokens"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'exchanged_access_token',
            'refresh_token': 'exchanged_refresh_token'
        }
        mock_dependencies['requests'].post.return_value = mock_response
        
        client = SchwabClient()
        result = client._exchange_code_for_tokens('test_code@')
        
        assert result is not None
        assert result['access_token'] == 'exchanged_access_token'
        assert result['refresh_token'] == 'exchanged_refresh_token'

    def test_exchange_code_for_tokens_failure(self, mock_dependencies):
        """Test code exchange fails with API error"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid code'
        mock_dependencies['requests'].post.return_value = mock_response
        
        client = SchwabClient()
        result = client._exchange_code_for_tokens('invalid_code@')
        
        assert result is None


class TestSchwabClientUtilityMethods:
    """Test utility methods and helper functions"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict(os.environ, {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.schwab_client.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class, \
             patch('system.algo_trader.schwab.schwab_client.requests') as mock_requests:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker,
                'requests': mock_requests
            }

    def test_get_auth_headers(self, mock_dependencies):
        """Test getting authentication headers"""
        mock_dependencies['broker'].get_access_token.return_value = 'test_token'
        
        client = SchwabClient()
        headers = client.get_auth_headers()
        
        expected_headers = {
            "Authorization": "Bearer test_token",
            "Accept": "application/json",
        }
        assert headers == expected_headers

    def test_make_authenticated_request(self, mock_dependencies):
        """Test making authenticated requests"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_dependencies['requests'].request.return_value = mock_response
        
        mock_dependencies['broker'].get_access_token.return_value = 'test_token'
        
        client = SchwabClient()
        response = client.make_authenticated_request('GET', 'https://api.test.com/test')
        
        assert response == mock_response
        
        # Verify request was made with proper headers
        mock_dependencies['requests'].request.assert_called_once()
        call_args = mock_dependencies['requests'].request.call_args
        assert call_args[0] == ('GET', 'https://api.test.com/test')
        assert 'headers' in call_args[1]
        assert call_args[1]['headers']['Authorization'] == 'Bearer test_token'

    def test_update_env_file_with_tokens(self, mock_dependencies):
        """Test updating environment file with new tokens"""
        tokens = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token'
        }
        
        # Mock existing env file content
        existing_content = 'export SCHWAB_API_KEY=test_key\nexport OTHER_VAR=value\n'
        
        with patch('builtins.open', mock_open(read_data=existing_content)) as mock_file:
            client = SchwabClient()
            client._update_env_file_with_tokens(tokens)
            
            # Verify file was opened for writing
            mock_file.assert_called_with(client.env_file_path, 'w')
            
            # Verify new content was written
            written_content = ''.join(call[0][0] for call in mock_file().write.call_args_list)
            assert 'export SCHWAB_ACCESS_TOKEN=new_access_token' in written_content
            assert 'export SCHWAB_REFRESH_TOKEN=new_refresh_token' in written_content
            assert 'export OTHER_VAR=value' in written_content  # Existing content preserved
