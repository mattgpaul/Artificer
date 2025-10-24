"""Redis broker for historical market data storage and retrieval.

This module provides the HistoricalMarketBroker class for caching historical
candle data and market hours information in Redis with TTL support.
"""

from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis import BaseRedisClient

# TTL constants in seconds
_DEFAULT_HISTORICAL_DATA_TTL = 86400  # 1 day
_MARKET_HOURS_TTL = 43200  # 12 hours


class HistoricalMarketBroker(BaseRedisClient):
    """Redis broker for historical market candle data.

    Manages storage and retrieval of historical price data with configurable
    TTL for cache expiration.

    Attributes:
        logger: Configured logger instance.
        namespace: Redis key namespace for historical data.
        ttl: Time-to-live for cached data in seconds.
    """

    def __init__(self, ttl: int = _DEFAULT_HISTORICAL_DATA_TTL) -> None:
        """Initialize historical market broker.

        Args:
            ttl: Time-to-live for cached data in seconds (default: 1 day).
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()
        self.ttl = ttl

    def _get_namespace(self) -> str:
        """Get the Redis namespace for this broker.

        Returns:
            Namespace string 'historical' for key prefixing.
        """
        return "historical"

    # TODO: This needs to be able to handle period and frequency designation
    def set_historical(self, ticker: str, data: list[dict]) -> bool:
        """Store historical candles data for a ticker.

        Args:
            ticker: Stock ticker symbol.
            data: List of candle dictionaries with OHLCV data.

        Returns:
            True if data was successfully stored, False otherwise.
        """
        success = self.set_json(key=ticker, value=data, ttl=self.ttl)
        if success:
            self.logger.debug(f"Set historical data for: {ticker}")
        return success

    def get_historical(self, ticker: str) -> list[dict]:
        """Retrieve historical candles data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            List of candle dictionaries, or empty list if not found.
        """
        data = self.get_json(key=ticker)
        self.logger.debug(f"Got historical data for: {ticker}")
        if not data:
            self.logger.warning(f"Cache miss: get_historical for {ticker}")
            return []
        return data

    # TODO: This is duplicated across 2 redis services. Find a way to consolidate
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
