from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

schwab = MarketHandler()
redis = LiveMarketBroker()

tickers = ['MSFT','AAPL','NVDA','AMD']

quotes = schwab.get_quotes(tickers)
schwab.logger.info(f"return: {quotes}")

for ticker in tickers:
    redis.set_quote(ticker, quotes[ticker])

data = redis.get_quote('MSFT')
redis.logger.info(f"{data}")