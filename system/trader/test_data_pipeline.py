from system.trader.redis.watchlist import WatchlistBroker
from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

schwab = MarketHandler()
redis = LiveMarketBroker()
watchlist = WatchlistBroker()

watchlist.set_watchlist(['MSFT','AAPL','NVDA','AMD'])

tickers = watchlist.get_watchlist()

hours = schwab.get_market_hours()
redis.set_market_hours(hours)
redis_response = redis.get_market_hours()
quotes = schwab.get_quotes(tickers)


redis.set_quotes(quotes)

data = redis.get_quotes('MSFT')

historical = schwab.get_price_history('MSFT')
print(historical)