"""Redis broker for historical market data storage and retrieval.

This module provides the HistoricalMarketBroker class for caching historical
candle data and market hours information in Redis with TTL support.
"""

from __future__ import annotations

from typing import Any

from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis_cache_client import RedisCacheClient

# TTL constants in seconds
_DEFAULT_HISTORICAL_DATA_TTL = 86400  # 1 day
_MARKET_HOURS_TTL = 43200  # 12 hours


class HistoricalMarketBroker(RedisCacheClient):
    """Redis broker for historical market candle data.

    Manages storage and retrieval of historical price data with configurable
    TTL for cache expiration.

    Attributes:
        logger: Configured logger instance.
        namespace: Redis key namespace for historical data.
        ttl: Time-to-live for cached data in seconds.
    """

    def __init__(self, ttl: int = _DEFAULT_HISTORICAL_DATA_TTL, config=None) -> None:
        """Initialize historical market broker.

        Args:
            ttl: Time-to-live for cached data in seconds (default: 1 day).
            config: Optional RedisConfig. If None, reads from environment.
        """
        super().__init__(config=config)
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
    def set_historical(self, ticker: str, data: list[dict[str, Any]]) -> bool:
        """Store historical candles data for a ticker.

        Args:
            ticker: Stock ticker symbol.
            data: List of candle dictionaries with OHLCV data.

        Returns:
            True if data was successfully stored, False otherwise.
        """
        result = self.set_json(ticker, data, ttl=self.ttl)
        if result:
            self.logger.debug(f"Set historical data for: {ticker}")
        return bool(result)

    def get_historical(self, ticker: str) -> list[dict[str, Any]]:
        """Retrieve historical candles data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            List of candle dictionaries, or empty list if not found or invalid.
        """
        data = self.get_json(ticker)
        self.logger.debug(f"Got historical data for: {ticker}")

        if data is None:
            self.logger.warning(f"Cache miss: get_historical for {ticker}")
            return []

        if not isinstance(data, list):
            return []
        return data

    # TODO: This is duplicated across 2 redis services. Find a way to consolidate
    def set_market_hours(self, market_hours: dict[str, str]) -> bool:
        """Store market hours information.

        Args:
            market_hours: Dictionary with market open/close times.

        Returns:
            True if successfully stored, False otherwise.
        """
        key = self._build_key("hours")

        result = self.client.hmset(key, mapping=market_hours)
        if result:
            # Apply TTL separately for the hash
            self.client.expire(key, _MARKET_HOURS_TTL)
        self.logger.debug(f"Set {market_hours} to {self.namespace}:'hours'")
        return bool(result)

    def get_market_hours(self) -> dict[str, str]:
        """Retrieve stored market hours information.

        Returns:
            Dictionary with market hours, or empty dict if not found.
        """
        key = self._build_key("hours")
        raw_hours = self.client.hgetall(key)
        self.logger.debug(f"Returned hours: {raw_hours}")

        if not raw_hours:
            self.logger.warning("Cache miss: market_hours")
            return {}

        # Decode bytes -> str if needed
        hours: dict[str, str] = {}
        for k, v in raw_hours.items():
            if isinstance(k, bytes):
                k_dec = k.decode("utf-8")
            else:
                k_dec = str(k)
            if isinstance(v, bytes):
                v_dec = v.decode("utf-8")
            else:
                v_dec = str(v)
            hours[k_dec] = v_dec

        return hours
