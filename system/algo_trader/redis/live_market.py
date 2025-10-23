from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis import BaseRedisClient


class LiveMarketBroker(BaseRedisClient):
    def __init__(self, ttl: int = 30):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()
        self.ttl = ttl

    def _get_namespace(self) -> str:
        return "live"

    def set_quotes(self, quotes_dict: dict) -> bool:
        operations = []
        for ticker, quote_data in quotes_dict.items():
            operations.append(("hmset", ticker, quote_data))
            operations.append(("expire", ticker, self.ttl))

        success = self.pipeline_execute(operations)
        self.logger.debug(f"Set {len(quotes_dict)} quotes via pipeline -> {success}")
        return success

    def get_quotes(self, tickers: list[str]) -> dict[str, str]:
        quotes = {}
        for ticker in tickers:
            quote_data = self.hgetall(ticker)
            if not quote_data:
                self.logger.warning(f"Cache miss: get_quotes {ticker}")
                quotes[ticker] = None
        self.logger.debug(f"Returned quotes: {quotes}")
        return quotes

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
