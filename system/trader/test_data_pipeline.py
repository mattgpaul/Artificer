from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

schwab = MarketHandler()
redis = LiveMarketBroker()

tickers = ['MSFT','AAPL','NVDA','AMD']

quotes = schwab.get_quotes(tickers)

redis.set_quotes(quotes)

data = redis.get_quotes('MSFT')