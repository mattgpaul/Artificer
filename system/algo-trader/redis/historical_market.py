from infrastructure.logging.logger import get_logger
from infrastructure.clients.redis_client import BaseRedisClient

class HistoricalMarketBroker(BaseRedisClient):
    def __init__(self, ttl: int = 86400):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()
        self.ttl = ttl

    def _get_namespace(self) -> str:
        return "historical"

    #TODO: This needs to be able to handle period and frequency designation
    def set_historical(self, ticker: str, data: list[dict]) -> bool:
        """Store historical candles data using base class JSON method."""
        success = self.set_json(key=ticker, value=data, ttl=self.ttl)
        if success:
            self.logger.debug(f"Set historical data for: {ticker}")
        return success

    def get_historical(self, ticker: str) -> list[dict]:
        """Retrieve historical candles data using base class JSON method."""
        data = self.get_json(key=ticker)
        self.logger.debug(f"Got historical data for: {ticker}")
        if not data:
            self.logger.warning(f"Cache miss: get_historical for {ticker}")
            return []
        return data

    #TODO: This is duplicated across 2 redis services. Find a way to consolidate
    def set_market_hours(self, market_hours: dict) -> bool:
        success = self.hmset(key="hours", mapping=market_hours, ttl=43200)
        self.logger.debug(f"Set {market_hours} to {self.namespace}:'hours'")
        return success

    def get_market_hours(self) -> dict[str, str]:
        hours = self.hgetall("hours")
        self.logger.debug(f"Returned hours: {hours}")
        if not hours:
            self.logger.warning("Cache miss: market_hours")
        return hours
