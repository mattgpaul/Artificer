"""Token manager for Schwab API authentication.

This module provides functionality to manage OAuth2 access tokens, including
token retrieval, refresh, and loading from environment variables.
"""

import base64
import time

import requests

from system.algo_trader.redis.account import AccountBroker
from system.algo_trader.schwab.schwab_base import SchwabBase
from system.algo_trader.schwab.oauth2_handler import OAuth2Handler

class TokenManager(SchwabBase):
    """Manages OAuth2 access tokens for Schwab API.

    Handles token lifecycle including retrieval, refresh, and validation.
    Uses distributed locking to prevent concurrent refresh operations.

    Args:
        api_key: Schwab API key (client ID).
        secret: Schwab API secret (client secret).
        base_url: Base URL for Schwab API.
        account_broker: AccountBroker instance for token storage.
        oauth2_handler: OAuth2Handler instance for token refresh.
        logger: Optional logger instance. If not provided, creates a new logger.
    """

    def __init__(self) -> None:
        """Initialize TokenManager with API credentials and handlers.

        Args:
            api_key: Schwab API key (client ID).
            secret: Schwab API secret (client secret).
            base_url: Base URL for Schwab API.
            account_broker: AccountBroker instance for token storage.
            oauth2_handler: OAuth2Handler instance for token refresh.
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        super().__init__()
        self.account_broker = AccountBroker()
        self.oauth2_handler = OAuth2Handler()

    def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Retrieves access token from Redis, or refreshes it if not available.
        Uses distributed locking to prevent concurrent refresh operations.

        Returns:
            Valid access token string.

        Raises:
            Exception: If token refresh fails or is blocked by another thread.
        """
        self.logger.debug("Attempting to get valid access token")

        access_token = self.account_broker.get_access_token()
        if access_token:
            self.logger.debug("Found valid access token in Redis")
            return access_token

        self.logger.info("No valid access token in Redis, attempting refresh")

        lock_name = "token-refresh"
        if self.account_broker.acquire_lock(lock_name, ttl=10, retry_interval=0.1, max_retries=50):
            try:
                access_token = self.account_broker.get_access_token()
                if access_token:
                    self.logger.info("Access token was refreshed by another thread")
                    return access_token

                self.logger.info("Lock acquired, refreshing token")

                if self.refresh_token():
                    access_token = self.account_broker.get_access_token()
                    if access_token:
                        self.logger.info("Successfully refreshed access token from Redis")
                        return access_token

                self.logger.info("Redis refresh failed, checking environment file")

                if self._load_token_from_config():
                    if self.refresh_token():
                        access_token = self.account_broker.get_access_token()
                        if access_token:
                            self.logger.info("Successfully refreshed access token from env file")
                            return access_token

                self.logger.warning("All refresh attempts failed, initiating OAuth2 flow")

                tokens = self.oauth2_handler.authenticate()
                if tokens and tokens.get("access_token"):
                    self.logger.info("OAuth2 flow completed successfully")
                    return tokens["access_token"]

                raise Exception("Unable to obtain valid access token after all attempts")
            finally:
                self.account_broker.release_lock(lock_name)
        else:
            self.logger.info("Another thread is refreshing token, waiting...")
            time.sleep(0.5)

            access_token = self.account_broker.get_access_token()
            if access_token:
                self.logger.info("Successfully retrieved access token refreshed by another thread")
                return access_token

            raise Exception("Token refresh by another thread failed")

    def refresh_token(self) -> bool:
        """Refresh access token using refresh token.

        Uses the stored refresh token to obtain a new access token from
        Schwab API and stores both tokens.

        Returns:
            True if refresh succeeds, False otherwise.
        """
        refresh_token = self.account_broker.get_refresh_token()
        if not refresh_token:
            self.logger.debug("No refresh token found in Redis")
            return False

        try:
            credentials = f"{self.api_key}:{self.secret}"
            headers = {
                "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}

            self.logger.debug("Sending token refresh request to Schwab API")
            response = requests.post(
                f"{self.base_url}/v1/oauth/token", headers=headers, data=payload
            )

            if response.status_code == 200:
                tokens = response.json()
                if "refresh_token" not in tokens:
                    tokens["refresh_token"] = refresh_token

                self.account_broker.set_access_token(tokens["access_token"])
                if tokens.get("refresh_token"):
                    self.account_broker.set_refresh_token(tokens["refresh_token"])

                self.logger.info("Successfully refreshed access token")
                return True
            else:
                self.logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to refresh token: {e}")

        return False

    def _load_token_from_config(self) -> bool:
        """Bootstrap Redis refresh token from config-backed attribute."""
        if not self.refresh_token:
            self.logger.debug("No refresh token present in SchwabConfig")
            return False

        try:
            ok = self.account_broker.set_refresh_token(self.refresh_token)
            if ok:
                self.logger.info("Loaded refresh token from config into Redis")
            else:
                self.logger.error("Failed to store refresh token in Redis")
            return ok
        except Exception as e:
            self.logger.error(f"Failed to load refresh token from config into Redis: {e}")
            return False
