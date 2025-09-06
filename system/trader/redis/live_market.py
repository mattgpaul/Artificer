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

    def set_quotes(self, quotes_dict: dict) -> bool:
        operations = [('hmset', ticker, quote_data) for ticker, quote_data in quotes_dict.items()]
        success = self.pipeline_execute(operations)
        self.logger.debug(f"Set {len(quotes_dict)} quotes via pipeline -> {success}")
        return success

    def get_quotes(self, ticker: str) -> StockQuote:
        quote = self.hgetall(ticker)
        self.logger.debug(f"Returned quote: {quote}")
        return StockQuote(**quote)