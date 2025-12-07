"""Unit tests for TokenManager – Schwab token lifecycle manager.

Tests focus on:
- get_valid_access_token happy paths (cache hit, lock-based refresh, wait-on-lock)
- refresh_token success and failure scenarios
- _load_token_from_config bootstrap behavior
All external dependencies are mocked via fixtures in ``conftest.py``.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestTokenManagerGetValidAccessToken:
    """Tests for TokenManager.get_valid_access_token."""

    def test_returns_existing_access_token_without_lock(
        self,
        token_manager_fixtures,
    ) -> None:
        """If Redis already has an access token, it should be returned immediately."""
        manager = token_manager_fixtures["manager"]
        broker = token_manager_fixtures["broker"]

        broker.get_access_token.return_value = "cached-token"

        token = manager.get_valid_access_token()

        assert token == "cached-token"
        broker.acquire_lock.assert_not_called()

    def test_refresh_path_with_lock_acquired_and_successful_refresh(
        self,
        token_manager_fixtures,
    ) -> None:
        """When no token exists, manager should acquire lock and refresh successfully."""
        manager = token_manager_fixtures["manager"]
        broker = token_manager_fixtures["broker"]
        refresh_mock = token_manager_fixtures["refresh_mock"]

        # First lookup (outside lock) -> no token
        # Second lookup (inside lock, before refresh) -> still no token
        # Third lookup (after refresh) -> new token
        broker.get_access_token.side_effect = [None, None, "new-token"]
        broker.acquire_lock.return_value = True
        refresh_mock.return_value = True

        token = manager.get_valid_access_token()

        assert token == "new-token"
        broker.acquire_lock.assert_called_once_with(
            "token-refresh",
            ttl=10,
            retry_interval=0.1,
            max_retries=50,
        )
        refresh_mock.assert_called_once()
        broker.release_lock.assert_called_once_with("token-refresh")

    def test_wait_for_other_thread_when_lock_not_acquired(
        self,
        token_manager_fixtures,
    ) -> None:
        """If lock cannot be acquired, manager waits and uses token set by another thread."""
        manager = token_manager_fixtures["manager"]
        broker = token_manager_fixtures["broker"]
        time_mod = token_manager_fixtures["time"]

        # First call outside lock sees no token
        # After waiting, token is available
        broker.get_access_token.side_effect = [None, "refreshed-by-other"]
        broker.acquire_lock.return_value = False

        token = manager.get_valid_access_token()

        assert token == "refreshed-by-other"
        time_mod.sleep.assert_called_once()

        # In this branch we never release a lock since we didn't acquire it
        broker.release_lock.assert_not_called()


@pytest.mark.unit
class TestTokenManagerRefreshToken:
    """Tests for TokenManager.refresh_token and _load_token_from_config."""

    def test_refresh_token_returns_false_when_no_refresh_token(
        self,
        token_manager_refresh_fixtures,
    ) -> None:
        """If Redis has no refresh token, refresh_token should return False."""
        manager = token_manager_refresh_fixtures["manager"]
        broker = token_manager_refresh_fixtures["broker"]

        broker.get_refresh_token.return_value = None

        # Call the underlying method directly to avoid name clash with attribute.
        from system.algo_trader.schwab.token_manager import TokenManager

        assert TokenManager.refresh_token(manager) is False

    def test_refresh_token_success_updates_access_and_refresh_tokens(
        self,
        token_manager_refresh_fixtures,
    ) -> None:
        """Successful HTTP 200 refresh should update both access and refresh tokens."""
        manager = token_manager_refresh_fixtures["manager"]
        broker = token_manager_refresh_fixtures["broker"]
        requests_mod = token_manager_refresh_fixtures["requests"]

        broker.get_refresh_token.return_value = "rt-current"

        response = requests_mod.post.return_value
        response.status_code = 200
        response.json.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
        }

        from system.algo_trader.schwab.token_manager import TokenManager

        assert TokenManager.refresh_token(manager) is True

        broker.set_access_token.assert_called_once_with("new-access")
        broker.set_refresh_token.assert_called_once_with("new-refresh")

    def test_refresh_token_success_without_refresh_token_in_response(
        self,
        token_manager_refresh_fixtures,
    ) -> None:
        """If response omits refresh_token, original refresh token is retained."""
        manager = token_manager_refresh_fixtures["manager"]
        broker = token_manager_refresh_fixtures["broker"]
        requests_mod = token_manager_refresh_fixtures["requests"]

        broker.get_refresh_token.return_value = "rt-original"

        response = requests_mod.post.return_value
        response.status_code = 200
        response.json.return_value = {
            "access_token": "new-access",
            # no refresh_token field
        }

        from system.algo_trader.schwab.token_manager import TokenManager

        assert TokenManager.refresh_token(manager) is True

        broker.set_access_token.assert_called_once_with("new-access")
        # Should have used the original refresh token
        broker.set_refresh_token.assert_called_once_with("rt-original")

    def test_refresh_token_failure_status_code_returns_false(
        self,
        token_manager_refresh_fixtures,
    ) -> None:
        """Non-200 HTTP status should log error and return False."""
        manager = token_manager_refresh_fixtures["manager"]
        broker = token_manager_refresh_fixtures["broker"]
        requests_mod = token_manager_refresh_fixtures["requests"]

        broker.get_refresh_token.return_value = "rt-current"

        response = requests_mod.post.return_value
        response.status_code = 400
        response.text = "Bad Request"

        from system.algo_trader.schwab.token_manager import TokenManager

        assert TokenManager.refresh_token(manager) is False
        broker.set_access_token.assert_not_called()
        broker.set_refresh_token.assert_not_called()

    def test_load_token_from_config_success(
        self,
        token_manager_refresh_fixtures,
    ) -> None:
        """_load_token_from_config should push refresh token from config into Redis."""
        manager = token_manager_refresh_fixtures["manager"]
        broker = token_manager_refresh_fixtures["broker"]

        manager.refresh_token = "rt-from-config"
        broker.set_refresh_token.return_value = True

        assert manager._load_token_from_config() is True
        broker.set_refresh_token.assert_called_once_with("rt-from-config")

    def test_load_token_from_config_no_token_returns_false(
        self,
        token_manager_refresh_fixtures,
    ) -> None:
        """If SchwabConfig has no refresh token, _load_token_from_config returns False."""
        manager = token_manager_refresh_fixtures["manager"]
        broker = token_manager_refresh_fixtures["broker"]

        manager.refresh_token = ""

        assert manager._load_token_from_config() is False
        broker.set_refresh_token.assert_not_called()


