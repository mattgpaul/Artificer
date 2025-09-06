from infrastructure.logging.logger import get_logger
from infrastructure.clients.redis_client import BaseRedisClient

class WatchlistBroker(BaseRedisClient):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()

    def _get_namespace(self) -> str:
        return "watchlist"

    def set_watchlist(self, tickers: list[str], strategy: str = "all") -> bool:
        #TODO: Not sure if "all" is the way to go. It will work for now
        success = self.sadd(strategy, *tickers)
        return success

    def get_watchlist(self, strategy: str = "all") -> set:
        dataset = self.smembers(key=strategy)
        self.logger.info(f"Current watchlist: {dataset}")
        return dataset