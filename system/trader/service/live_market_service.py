import sys
import signal
import time
import argparse
from datetime import datetime

from infrastructure.logging.logger import get_logger
from system.trader.redis.watchlist import WatchlistBroker
from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

class LiveMarketService:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.running = True
        self._setup_signal_handlers()
        self._setup_clients()

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        self.logger.info(f"Received signal {signum}, sutting down gracefully...")
        self.running = False

    def _setup_clients(self):
        try:
            self.logger.info("Setting up clients")
            self.market_handler = MarketHandler()
            self.market_broker = LiveMarketBroker()
            self.watchlist_broker = WatchlistBroker()
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            raise

    def _get_sleep_interval(self) -> int:
        pass

    def _execute_pipeline(self) -> bool:
        pass

    def run(self):
        pass

    def health_check(self) -> bool:
        pass

def main():
    pass

if __name__ == "__main__":
    sys.exit(main())





####### Old #############
schwab = MarketHandler()
redis = LiveMarketBroker()
watchlist = WatchlistBroker()

tickers = watchlist.get_watchlist()

hours = schwab.get_market_hours()
redis.set_market_hours(hours)
redis_response = redis.get_market_hours()
quotes = schwab.get_quotes(tickers)


redis.set_quotes(quotes)

data = redis.get_quotes('MSFT')
