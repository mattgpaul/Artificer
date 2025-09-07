from datetime import datetime, timedelta
from system.trader.redis.watchlist import WatchlistBroker
from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

schwab = MarketHandler()
redis = LiveMarketBroker()
watchlist = WatchlistBroker()

tickers = watchlist.get_watchlist()

today = datetime.now()
monday = today + timedelta(days=(7 - today.weekday()))
hours = schwab.get_market_hours(monday)
#redis.set_market_hours(hours)
redis_response = redis.get_market_hours()
print(redis_response)
quotes = schwab.get_quotes(tickers)


redis.set_quotes(quotes)

data = redis.get_quotes(['MSFT'])
