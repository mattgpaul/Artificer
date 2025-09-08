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
