from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

schwab = MarketHandler()
redis = LiveMarketBroker()

tickers = ['MSFT','AAPL','NVDA','AMD']

hours = schwab.get_market_hours()
redis.set_market_hours(hours)
redis_response = redis.get_market_hours()
print(redis_response)
quotes = schwab.get_quotes(tickers)


redis.set_quotes(quotes)

data = redis.get_quotes('MSFT')