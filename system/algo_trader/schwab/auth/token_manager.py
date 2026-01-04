"""Token manager for Schwab API authentication.

This module provides functionality to manage OAuth2 access tokens, including
token retrieval, refresh, and loading from environment variables.
"""

import base64
import os
import time

import requests

from infrastructure.logging.logger import get_logger
from system.algo_trader.infra.redis.account import AccountBroker
from system.algo_trader.schwab.auth.oauth2 import OAuth2Handler


class TokenManager:
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

    def __init__(
        self,
        api_key: str,
        secret: str,
        base_url: str,
        account_broker: AccountBroker,
        oauth2_handler: OAuth2Handler,
        logger=None,
    ):
        """Initialize TokenManager with API credentials and handlers.

        Args:
            api_key: Schwab API key (client ID).
            secret: Schwab API secret (client secret).
            base_url: Base URL for Schwab API.
            account_broker: AccountBroker instance for token storage.
            oauth2_handler: OAuth2Handler instance for token refresh.
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.api_key = api_key
        self.secret = secret
        self.base_url = base_url
        self.account_broker = account_broker
        self.oauth2_handler = oauth2_handler
        self.logger = logger or get_logger(self.__class__.__name__)

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

                if self.load_token():
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

    def load_token(self) -> bool:
        """Load refresh token from environment variable.

        Attempts to load refresh token from SCHWAB_REFRESH_TOKEN environment
        variable and store it in Redis.

        Returns:
            True if token was loaded successfully, False otherwise.
        """
        try:
            refresh_token = os.getenv("SCHWAB_REFRESH_TOKEN")
            if refresh_token:
                self.account_broker.set_refresh_token(refresh_token)
                self.logger.info("Loaded refresh token from environment and stored in Redis")
                return True
        except Exception as e:
            self.logger.error(f"Failed to load refresh token from env: {e}")

        return False
