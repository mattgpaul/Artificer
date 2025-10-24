"""Redis broker for watchlist management.

This module provides the WatchlistBroker class for managing stock watchlists
in Redis using set operations, with TTL support for automatic expiration.
"""

from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis import BaseRedisClient


class WatchlistBroker(BaseRedisClient):
    """Redis broker for stock watchlist management.

    Manages watchlists using Redis set operations, allowing storage of
    ticker symbols organized by strategy.

    Attributes:
        logger: Configured logger instance.
        namespace: Redis key namespace for watchlist data.
        ttl: Time-to-live for watchlist data in seconds.
    """

    def __init__(self, ttl: int | None = None, config=None) -> None:
        """Initialize watchlist broker.

        Args:
            ttl: Optional time-to-live for watchlist data in seconds.
            config: Optional RedisConfig. If None, reads from environment.
        """
        super().__init__(config=config)
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()
        self.ttl = ttl

    def _get_namespace(self) -> str:
        """Get the Redis namespace for this broker.

        Returns:
            Namespace string 'watchlist' for key prefixing.
        """
        return "watchlist"

    def set_watchlist(self, tickers: list[str], strategy: str = "all") -> bool:
        """Store tickers in a strategy-specific watchlist.

        Args:
            tickers: List of ticker symbols to add to watchlist.
            strategy: Strategy name to organize watchlist (default: 'all').

        Returns:
            True if tickers were successfully added, False otherwise.
        """
        # TODO: Not sure if "all" is the way to go. It will work for now
        success = self.sadd(strategy, *tickers, ttl=self.ttl)
        return success

    def get_watchlist(self, strategy: str = "all") -> set:
        """Retrieve tickers from a strategy-specific watchlist.

        Args:
            strategy: Strategy name to retrieve watchlist for (default: 'all').

        Returns:
            Set of ticker symbols in the watchlist.
        """
        dataset = self.smembers(key=strategy)
        self.logger.info(f"Current watchlist: {dataset}")
        return dataset
