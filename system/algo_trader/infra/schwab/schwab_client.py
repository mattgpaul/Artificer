"""Schwab API Client - Consolidated OAuth2 and Token Management.

This module provides the core Schwab API client with Redis-first token management,
proper OAuth2 flow, and automatic token refresh capabilities.

Token Flow:
1. Check Redis for valid access token (TTL: 30 min)
2. If expired, check Redis for refresh token (TTL: 90 days) → refresh access token
3. If refresh token missing from Redis, load from env and store in Redis → refresh
4. If refresh token expired, initiate OAuth2 flow → save to Redis, display for manual save
"""

import os
from typing import Any

import requests

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger
from system.algo_trader.infra.redis.account import AccountBroker
from system.algo_trader.infra.schwab.auth.oauth2 import OAuth2Handler
from system.algo_trader.infra.schwab.auth.token_manager import TokenManager


class SchwabClient(Client):
    """Consolidated Schwab API client with Redis-first token management.

    This client handles OAuth2 authentication, token refresh, and provides
    a base for Schwab API operations. Tokens are stored in Redis with proper
    TTL management. Refresh tokens must be persisted manually via environment
    variables as Redis is ephemeral.
    """

    def __init__(self):
        """Initialize Schwab client with environment configuration."""
        self.logger = get_logger(self.__class__.__name__)

        self.api_key = os.getenv("SCHWAB_API_KEY")
        self.secret = os.getenv("SCHWAB_SECRET")
        self.app_name = os.getenv("SCHWAB_APP_NAME")
        self.base_url = "https://api.schwabapi.com"

        if not all([self.api_key, self.secret, self.app_name]):
            raise ValueError(
                "Missing required Schwab environment variables. "
                "Please set SCHWAB_API_KEY, SCHWAB_SECRET, and SCHWAB_APP_NAME"
            )

        self.account_broker = AccountBroker()

        self.oauth2_handler = OAuth2Handler(
            self.api_key, self.secret, self.base_url, self.account_broker, self.logger
        )
        self.token_manager = TokenManager(
            self.api_key,
            self.secret,
            self.base_url,
            self.account_broker,
            self.oauth2_handler,
            self.logger,
        )

        self.logger.info("SchwabClient initialized successfully")

    def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        This method implements the complete token lifecycle with distributed locking
        to prevent multiple threads from refreshing simultaneously:
        1. Check Redis for valid access token
        2. If expired/missing, acquire lock and attempt refresh
        3. If lock not acquired, wait for other thread to complete refresh
        4. If refresh token missing, load from env file and store in Redis
        5. If refresh token expired, initiate OAuth2 flow

        Returns:
            str: Valid access token

        Raises:
            Exception: If unable to obtain valid token after all attempts
        """
        return self.token_manager.get_valid_access_token()

    def refresh_token(self) -> bool:
        """Refresh access token using stored refresh token.

        Returns:
            bool: True if refresh was successful, False otherwise
        """
        return self.token_manager.refresh_token()

    def load_token(self) -> bool:
        """Load refresh token from environment and store in Redis.

        Returns:
            bool: True if refresh token was loaded and stored, False otherwise
        """
        return self.token_manager.load_token()

    def authenticate(self) -> dict[str, Any] | None:
        """Perform complete OAuth2 authentication flow.

        Returns:
            Dict containing tokens if successful, None otherwise
        """
        return self.oauth2_handler.authenticate()

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dict containing Authorization header with valid access token
        """
        token = self.get_valid_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def make_authenticated_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an authenticated HTTP request to the Schwab API.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL for the request
            **kwargs: Additional arguments to pass to requests

        Returns:
            requests.Response object
        """
        headers = self.get_auth_headers()
        if "headers" in kwargs:
            headers.update(kwargs["headers"])

        kwargs["headers"] = headers

        self.logger.debug(f"Making {method} request to {url}")
        return requests.request(method, url, **kwargs)
