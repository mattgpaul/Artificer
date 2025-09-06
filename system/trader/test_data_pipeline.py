from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

import logging
logging.getLogger().setLevel(logging.DEBUG)

schwab = MarketHandler()
redis = LiveMarketBroker()

tickers = ['MSFT','AAPL','NVDA','AMD']

quotes = schwab.get_quotes(tickers)
schwab.logger.info(f"return: {quotes}")
