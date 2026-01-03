"""Redis broker for live market data quotes and watchlists.

This module provides the LiveMarketBroker class for caching real-time stock
quotes and market hours information in Redis with TTL support.
"""

from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis import BaseRedisClient

# TTL constants in seconds
_DEFAULT_LIVE_QUOTE_TTL = 30  # 30 seconds for real-time quotes
_MARKET_HOURS_TTL = 43200  # 12 hours


class LiveMarketBroker(BaseRedisClient):
    """Redis broker for live market quote data.

    Manages storage and retrieval of real-time stock quotes with short TTL
    for rapid updates.

    Attributes:
        logger: Configured logger instance.
        namespace: Redis key namespace for live data.
        ttl: Time-to-live for cached quotes in seconds.
    """

    def __init__(self, ttl: int = _DEFAULT_LIVE_QUOTE_TTL, config=None) -> None:
        """Initialize live market broker.

        Args:
            ttl: Time-to-live for cached quotes in seconds (default: 30).
            config: Optional RedisConfig. If None, reads from environment.
        """
        super().__init__(config=config)
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()
        self.ttl = ttl

    def _get_namespace(self) -> str:
        """Get the Redis namespace for this broker.

        Returns:
            Namespace string 'live' for key prefixing.
        """
        return "live"

    def set_quotes(self, quotes_dict: dict) -> bool:
        """Store multiple stock quotes using Redis pipeline.

        Args:
            quotes_dict: Dictionary mapping ticker symbols to quote data dicts.

        Returns:
            True if all quotes were successfully stored, False otherwise.
        """
        operations = []
        for ticker, quote_data in quotes_dict.items():
            operations.append(("hmset", ticker, quote_data))
            operations.append(("expire", ticker, self.ttl))

        success = self.pipeline_execute(operations)
        self.logger.debug(f"Set {len(quotes_dict)} quotes via pipeline -> {success}")
        return success

    def get_quotes(self, tickers: list[str]) -> dict[str, str]:
        """Retrieve quotes for multiple tickers.

        Args:
            tickers: List of ticker symbols to retrieve.

        Returns:
            Dictionary mapping tickers to quote data, with None for cache misses.
        """
        quotes = {}
        for ticker in tickers:
            quote_data = self.hgetall(ticker)
            if not quote_data:
                self.logger.warning(f"Cache miss: get_quotes {ticker}")
                quotes[ticker] = None
        self.logger.debug(f"Returned quotes: {quotes}")
        return quotes

    def set_market_hours(self, market_hours: dict) -> bool:
        """Store market hours information.

        Args:
            market_hours: Dictionary with market open/close times.

        Returns:
            True if successfully stored, False otherwise.
        """
        success = self.hmset(key="hours", mapping=market_hours, ttl=_MARKET_HOURS_TTL)
        self.logger.debug(f"Set {market_hours} to {self.namespace}:'hours'")
        return success

    def get_market_hours(self) -> dict[str, str]:
        """Retrieve stored market hours information.

        Returns:
            Dictionary with market hours, or empty dict if not found.
        """
        hours = self.hgetall("hours")
        self.logger.debug(f"Returned hours: {hours}")
        if not hours:
            self.logger.warning("Cache miss: market_hours")
        return hours
