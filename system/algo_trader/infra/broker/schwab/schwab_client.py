"""Schwab API Client - Consolidated OAuth2 and Token Management.

This module provides the core Schwab API client with Redis-first token management,
proper OAuth2 flow, and automatic token refresh capabilities.

Token Flow:
1. Check Redis for valid access token (TTL: 30 min)
2. If expired, check Redis for refresh token (TTL: 90 days) → refresh access token
3. If refresh token missing from Redis, load from env and store in Redis → refresh
4. If refresh token expired, initiate OAuth2 flow → save to Redis, display for manual save
"""
import requests

from system.algo_trader.infra.broker.schwab.schwab_base import SchwabBase
from system.algo_trader.infra.broker.schwab.token_manager import TokenManager


class SchwabClient(SchwabBase):
    """Consolidated Schwab API client with Redis-first token management.

    This client handles OAuth2 authentication, token refresh, and provides
    a base for Schwab API operations. Tokens are stored in Redis with proper
    TTL management. Refresh tokens must be persisted manually via environment
    variables as Redis is ephemeral.
    """

    def __init__(self) -> None:
        """Initialize Schwab client with environment configuration."""
        super().__init__()
        self.token_manager = TokenManager()

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dict containing Authorization header with valid access token
        """
        token = self.token_manager.get_valid_access_token()
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
