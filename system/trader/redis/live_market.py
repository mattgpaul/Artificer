import redis
from component.software.finance.stock import StockQuote
from infrastructure.logging.logger import get_logger
from infrastructure.clients.redis_client import BaseRedisClient

class LiveMarketBroker(BaseRedisClient):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)

        self.namespace = self._get_namespace()

    def _get_namespace(self) -> str:
        return "live"

    def set_quote(self, ticker: str, data: dict) -> bool:
        self.logger.debug(f"Data to set: {data}")
        success = self.hmset(f"{ticker}", data)
        return success

    def get_quote(self, ticker: str) -> StockQuote:
        quote = self.hgetall(ticker)
        self.logger.debug(f"Returned quote: {quote}")
        return StockQuote(**quote)