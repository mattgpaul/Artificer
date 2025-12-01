"""Redis broker for account data storage and retrieval.

This module provides the AccountBroker class for caching Schwab account
information including positions and balances in Redis with TTL support.
"""

from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis_cache_client import RedisCacheClient

# TTL constants
_REFRESH_TOKEN_TTL = 90 * 24 * 60  # 90 days
_ACCESS_TOKEN_TTL = 30 * 60  # 30 minutes


class AccountBroker(RedisCacheClient):
    """Redis broker for Schwab OAuth token management.

    Manages storage and retrieval of Schwab API OAuth tokens with appropriate
    TTL values for access and refresh tokens.

    Attributes:
        logger: Configured logger instance.
        namespace: Redis key namespace for account data.
    """

    def __init__(self, config=None) -> None:
        """Initialize account broker.

        Args:
            config: Optional RedisConfig. If None, reads from environment.
        """
        super().__init__(config=config)
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
        ttl = _REFRESH_TOKEN_TTL
        return self.set("refresh-token", token, ttl=ttl)

    def get_refresh_token(self) -> str:
        """Retrieve stored Schwab API refresh token.

        Returns:
            Refresh token string, or None if not found.
        """
        return self.get("refresh-token")

    def set_access_token(self, token: str, ttl: int = _ACCESS_TOKEN_TTL) -> bool:
        """Store Schwab API access token with custom expiration.

        Args:
            token: OAuth access token string.
            ttl: Time-to-live in seconds (default: 30 minutes).

        Returns:
            True if token was successfully stored, False otherwise.
        """
        return self.set("access-token", token, ttl=ttl)

    def get_access_token(self) -> str:
        """Retrieve stored Schwab API access token.

        Returns:
            Access token string, or None if not found.
        """
        return self.get("access-token")
