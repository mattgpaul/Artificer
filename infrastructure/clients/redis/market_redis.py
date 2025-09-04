import logging
from infrastructure.clients.redis_client import BaseRedisClient

class MarketRedis(BaseRedisClient):
    def _get_namespace(self) -> str:
        return "market"

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    
    market = MarketRedis()
    ping_result = market.ping()
    add_result = market.sadd("watchlist", "AAPL", "MSFT", "GOOGL")
    tickers = market.smembers("watchlist")
    market.set("test:price", "150.25")
    price = market.get("test:price")