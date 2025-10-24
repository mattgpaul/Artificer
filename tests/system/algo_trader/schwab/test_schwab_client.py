"""Unit tests for SchwabClient - OAuth2 and Token Management.

Tests cover token lifecycle, OAuth2 flow, and error handling scenarios.
All external dependencies are mocked to avoid network calls.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.schwab.schwab_client import SchwabClient


class TestSchwabClientInitialization:
    """Test SchwabClient initialization and configuration validation."""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables."""
        with patch.dict(
            os.environ,
            {
                "SCHWAB_API_KEY": "test_api_key",
                "SCHWAB_SECRET": "test_secret",
                "SCHWAB_APP_NAME": "test_app_name",
            },
        ):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies."""
        with (
            patch("system.algo_trader.schwab.schwab_client.get_logger") as mock_logger,
            patch("system.algo_trader.schwab.schwab_client.AccountBroker") as mock_broker_class,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "broker_class": mock_broker_class,
                "broker": mock_broker,
            }

    def test_initialization_success(self, mock_dependencies):
        """Test successful SchwabClient initialization."""
        client = SchwabClient()

        assert client.api_key == "test_api_key"
        assert client.secret == "test_secret"
        assert client.app_name == "test_app_name"
        assert client.base_url == "https://api.schwabapi.com"
        assert client.account_broker is not None

    def test_initialization_missing_env_vars(self):
        """Test initialization fails with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required Schwab environment variables"):
                SchwabClient()

    def test_initialization_partial_env_vars(self):
        """Test initialization fails with partial environment variables."""
        with patch.dict(
            os.environ,
            {
                "SCHWAB_API_KEY": "test_key",
                # Missing SCHWAB_SECRET and SCHWAB_APP_NAME
            },
        ):
            with pytest.raises(ValueError, match="Missing required Schwab environment variables"):
                SchwabClient()


class TestSchwabClientTokenManagement:
    """Test token lifecycle and refresh functionality."""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables."""
        with patch.dict(
            os.environ,
            {
                "SCHWAB_API_KEY": "test_api_key",
                "SCHWAB_SECRET": "test_secret",
                "SCHWAB_APP_NAME": "test_app_name",
            },
        ):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies."""
        with (
            patch("system.algo_trader.schwab.schwab_client.get_logger") as mock_logger,
            patch("system.algo_trader.schwab.schwab_client.AccountBroker") as mock_broker_class,
            patch("system.algo_trader.schwab.schwab_client.requests") as mock_requests,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "broker_class": mock_broker_class,
                "broker": mock_broker,
                "requests": mock_requests,
            }

    def test_get_valid_access_token_from_redis(self, mock_dependencies):
        """Test getting valid access token from Redis."""
        mock_dependencies["broker"].get_access_token.return_value = "valid_token"

        client = SchwabClient()
        token = client.get_valid_access_token()

        assert token == "valid_token"
        mock_dependencies["broker"].get_access_token.assert_called()

    def test_get_valid_access_token_with_refresh(self, mock_dependencies):
        """Test getting access token via refresh when Redis token is expired."""
        # First call returns None (expired), second call returns new token
        mock_dependencies["broker"].get_access_token.side_effect = [None, "refreshed_token"]
        mock_dependencies["broker"].get_refresh_token.return_value = "refresh_token"

        # Mock successful refresh response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "refresh_token": "refresh_token",
        }
        mock_dependencies["requests"].post.return_value = mock_response

        client = SchwabClient()
        token = client.get_valid_access_token()

        assert token == "refreshed_token"

    def test_get_auth_headers_triggers_refresh(self, mock_dependencies):
        """Test get_auth_headers method that internally calls get_valid_access_token."""
        # This tests that the full flow works when getting auth headers
        mock_dependencies["broker"].get_access_token.return_value = "valid_token"

        client = SchwabClient()
        headers = client.get_auth_headers()

        assert headers["Authorization"] == "Bearer valid_token"
        assert headers["Accept"] == "application/json"

    def test_refresh_token_success(self, mock_dependencies):
        """Test successful token refresh using Redis refresh token."""
        # Setup mocks
        mock_dependencies["broker"].get_refresh_token.return_value = "refresh_token"

        # Mock successful refresh response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
        }
        mock_dependencies["requests"].post.return_value = mock_response

        client = SchwabClient()
        result = client.refresh_token()

        assert result is True
        mock_dependencies["broker"].set_access_token.assert_called_with("new_access_token")
        mock_dependencies["broker"].set_refresh_token.assert_called_with("new_refresh_token")

    def test_refresh_token_no_refresh_token(self, mock_dependencies):
        """Test refresh fails when no refresh token in Redis."""
        mock_dependencies["broker"].get_refresh_token.return_value = None

        client = SchwabClient()
        result = client.refresh_token()

        assert result is False

    def test_refresh_token_api_failure(self, mock_dependencies):
        """Test refresh fails when API returns error."""
        mock_dependencies["broker"].get_refresh_token.return_value = "refresh_token"

        # Mock failed refresh response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_dependencies["requests"].post.return_value = mock_response

        client = SchwabClient()
        result = client.refresh_token()

        assert result is False

    def test_refresh_token_keeps_original_when_not_in_response(self, mock_dependencies):
        """Test refresh keeps original refresh token when not in API response."""
        mock_dependencies["broker"].get_refresh_token.return_value = "original_refresh_token"

        # Mock refresh response without refresh_token
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token"
            # No refresh_token in response
        }
        mock_dependencies["requests"].post.return_value = mock_response

        client = SchwabClient()
        result = client.refresh_token()

        assert result is True
        mock_dependencies["broker"].set_access_token.assert_called_with("new_access_token")
        # Should still set the original refresh token
        assert mock_dependencies["broker"].set_refresh_token.called

    def test_load_token_success(self, mock_dependencies):
        """Test loading refresh token from environment variables."""
        with patch.dict(
            os.environ,
            {
                "SCHWAB_API_KEY": "test_api_key",
                "SCHWAB_SECRET": "test_secret",
                "SCHWAB_APP_NAME": "test_app_name",
                "SCHWAB_REFRESH_TOKEN": "env_refresh_token",
            },
        ):
            client = SchwabClient()
            result = client.load_token()

            assert result is True
            mock_dependencies["broker"].set_refresh_token.assert_called_with("env_refresh_token")

    def test_load_token_missing(self, mock_dependencies):
        """Test loading token fails when not in environment."""
        client = SchwabClient()
        result = client.load_token()

        assert result is False

    def test_refresh_token_exception_handling(self, mock_dependencies):
        """Test refresh token handles exceptions gracefully."""
        mock_dependencies["broker"].get_refresh_token.return_value = "refresh_token"
        mock_dependencies["requests"].post.side_effect = Exception("Network error")

        client = SchwabClient()
        result = client.refresh_token()

        assert result is False


class TestSchwabClientOAuth2Flow:
    """Test OAuth2 authentication flow."""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables."""
        with patch.dict(
            os.environ,
            {
                "SCHWAB_API_KEY": "test_api_key",
                "SCHWAB_SECRET": "test_secret",
                "SCHWAB_APP_NAME": "test_app_name",
            },
        ):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies."""
        with (
            patch("system.algo_trader.schwab.schwab_client.get_logger") as mock_logger,
            patch("system.algo_trader.schwab.schwab_client.AccountBroker") as mock_broker_class,
            patch("system.algo_trader.schwab.schwab_client.requests") as mock_requests,
            patch("builtins.input") as mock_input,
            patch("builtins.print") as mock_print,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "broker_class": mock_broker_class,
                "broker": mock_broker,
                "requests": mock_requests,
                "input": mock_input,
                "print": mock_print,
            }

    def test_authenticate_success(self, mock_dependencies):
        """Test successful OAuth2 flow."""
        # Mock user input - first for redirect URL, second for confirmation
        mock_dependencies["input"].side_effect = [
            "https://127.0.0.1/?code=test_code%40",
            "",  # User presses ENTER after copying token
        ]

        # Mock successful token exchange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "oauth_access_token",
            "refresh_token": "oauth_refresh_token",
        }
        mock_dependencies["requests"].post.return_value = mock_response

        client = SchwabClient()
        result = client.authenticate()

        assert result is not None
        assert result["access_token"] == "oauth_access_token"
        assert result["refresh_token"] == "oauth_refresh_token"

        # Verify tokens were stored
        mock_dependencies["broker"].set_access_token.assert_called_with("oauth_access_token")
        mock_dependencies["broker"].set_refresh_token.assert_called_with("oauth_refresh_token")

        # Verify print was called to display token instructions
        assert mock_dependencies["print"].called

    def test_authenticate_invalid_url(self, mock_dependencies):
        """Test OAuth2 flow fails with invalid redirect URL."""
        mock_dependencies["input"].return_value = "invalid_url"

        client = SchwabClient()
        result = client.authenticate()

        assert result is None

    def test_authenticate_empty_url(self, mock_dependencies):
        """Test OAuth2 flow fails with empty redirect URL."""
        mock_dependencies["input"].return_value = ""

        client = SchwabClient()
        result = client.authenticate()

        assert result is None

    def test_authenticate_url_without_code(self, mock_dependencies):
        """Test OAuth2 flow fails when redirect URL doesn't contain code."""
        mock_dependencies["input"].return_value = "https://127.0.0.1/?error=access_denied"

        client = SchwabClient()
        result = client.authenticate()

        assert result is None

    def test_exchange_code_for_tokens_success(self, mock_dependencies):
        """Test successful code exchange for tokens."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "exchanged_access_token",
            "refresh_token": "exchanged_refresh_token",
        }
        mock_dependencies["requests"].post.return_value = mock_response

        client = SchwabClient()
        result = client._exchange_code_for_tokens("test_code@")

        assert result is not None
        assert result["access_token"] == "exchanged_access_token"
        assert result["refresh_token"] == "exchanged_refresh_token"

    def test_exchange_code_for_tokens_failure(self, mock_dependencies):
        """Test code exchange fails with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid code"
        mock_dependencies["requests"].post.return_value = mock_response

        client = SchwabClient()
        result = client._exchange_code_for_tokens("invalid_code@")

        assert result is None


class TestSchwabClientUtilityMethods:
    """Test utility methods and helper functions."""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables."""
        with patch.dict(
            os.environ,
            {
                "SCHWAB_API_KEY": "test_api_key",
                "SCHWAB_SECRET": "test_secret",
                "SCHWAB_APP_NAME": "test_app_name",
            },
        ):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies."""
        with (
            patch("system.algo_trader.schwab.schwab_client.get_logger") as mock_logger,
            patch("system.algo_trader.schwab.schwab_client.AccountBroker") as mock_broker_class,
            patch("system.algo_trader.schwab.schwab_client.requests") as mock_requests,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "broker_class": mock_broker_class,
                "broker": mock_broker,
                "requests": mock_requests,
            }

    def test_get_auth_headers(self, mock_dependencies):
        """Test getting authentication headers."""
        mock_dependencies["broker"].get_access_token.return_value = "test_token"

        client = SchwabClient()
        headers = client.get_auth_headers()

        expected_headers = {
            "Authorization": "Bearer test_token",
            "Accept": "application/json",
        }
        assert headers == expected_headers

    def test_make_authenticated_request(self, mock_dependencies):
        """Test making authenticated requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_dependencies["requests"].request.return_value = mock_response

        mock_dependencies["broker"].get_access_token.return_value = "test_token"

        client = SchwabClient()
        response = client.make_authenticated_request("GET", "https://api.test.com/test")

        assert response == mock_response

        # Verify request was made with proper headers
        mock_dependencies["requests"].request.assert_called_once()
        call_args = mock_dependencies["requests"].request.call_args
        assert call_args[0] == ("GET", "https://api.test.com/test")
        assert "headers" in call_args[1]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_token"

    def test_display_refresh_token_instructions(self, mock_dependencies):
        """Test display of refresh token instructions with user confirmation."""
        test_token = "test_refresh_token_12345"

        # Mock both input and print
        with (
            patch("builtins.input", return_value="") as mock_input,
            patch("builtins.print") as mock_print,
        ):
            client = SchwabClient()
            client._display_refresh_token_instructions(test_token)

            # Verify print was called with token instructions
            assert mock_print.called
            print_calls = [str(call) for call in mock_print.call_args_list]
            print_output = " ".join(print_calls)

            # Check that key elements are in the output
            assert "OAUTH2 FLOW COMPLETE" in print_output
            assert test_token in print_output
            assert "SCHWAB_REFRESH_TOKEN" in print_output
            assert "Redis is ephemeral" in print_output

            # Verify input was called for user confirmation
            mock_input.assert_called_once()

            # Verify logger was called to confirm user action
            mock_dependencies["logger_instance"].info.assert_called_with(
                "User confirmed token copied"
            )
