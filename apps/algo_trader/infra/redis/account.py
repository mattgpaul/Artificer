"""Redis broker for Schwab token storage."""

from __future__ import annotations

from infrastructure.redis.redis import BaseRedisClient

# Token TTLs aligned with SchwabClient expectations
ACCESS_TOKEN_TTL_SECONDS = 30 * 60  # 30 minutes
REFRESH_TOKEN_TTL_SECONDS = 90 * 24 * 60 * 60  # 90 days


class AccountBroker(BaseRedisClient):
    """Broker responsible for Schwab token storage and locking."""

    def _get_namespace(self) -> str:
        # Single namespace for algo_trader token-related keys
        return "algo_trader"

    # Access token operations
    def get_access_token(self) -> str | None:
        """Return the cached Schwab access token, if present."""
        return self.get("schwab:access_token")

    def set_access_token(self, token: str) -> bool:
        """Cache the Schwab access token with the standard TTL."""
        return self.set("schwab:access_token", token, ttl=ACCESS_TOKEN_TTL_SECONDS)

    # Refresh token operations
    def get_refresh_token(self) -> str | None:
        """Return the cached Schwab refresh token, if present."""
        return self.get("schwab:refresh_token")

    def set_refresh_token(self, token: str) -> bool:
        """Cache the Schwab refresh token with the standard TTL."""
        return self.set("schwab:refresh_token", token, ttl=REFRESH_TOKEN_TTL_SECONDS)
