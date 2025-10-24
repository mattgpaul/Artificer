"""Redis broker for account data storage and retrieval.

This module provides the AccountBroker class for caching Schwab account
information including positions and balances in Redis with TTL support.
"""

from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis import BaseRedisClient


class AccountBroker(BaseRedisClient):
    """Redis broker for Schwab OAuth token management.

    Manages storage and retrieval of Schwab API OAuth tokens with appropriate
    TTL values for access and refresh tokens.

    Attributes:
        logger: Configured logger instance.
        namespace: Redis key namespace for account data.
    """

    def __init__(self) -> None:
        """Initialize account broker."""
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()

    def _get_namespace(self) -> str:
        """Get the Redis namespace for this broker.

        Returns:
            Namespace string 'account' for key prefixing.
        """
        return "account"

    def set_refresh_token(self, token: str) -> bool:
        """Store Schwab API refresh token with 90-day expiration.

        Args:
            token: OAuth refresh token string.

        Returns:
            True if token was successfully stored, False otherwise.
        """
        ttl = 90 * 24 * 60 * 60  # 90 days in seconds
        success = self.set(key="refresh-token", value=token, ttl=ttl)
        return success

    def get_refresh_token(self) -> str:
        """Retrieve stored Schwab API refresh token.

        Returns:
            Refresh token string, or None if not found.
        """
        token = self.get("refresh-token")
        return token

    def set_access_token(self, token: str, ttl: int = 30) -> bool:
        """Store Schwab API access token with custom expiration.

        Args:
            token: OAuth access token string.
            ttl: Time-to-live in minutes (default: 30).

        Returns:
            True if token was successfully stored, False otherwise.
        """
        success = self.set(key="access-token", value=token, ttl=ttl * 60)
        return success

    def get_access_token(self) -> str:
        """Retrieve stored Schwab API access token.

        Returns:
            Access token string, or None if not found.
        """
        token = self.get("access-token")
        return token
