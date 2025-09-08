import pandas as pd

from infrastructure.logging.logger import get_logger
from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.watchlist import WatchlistBroker
from system.trader.redis.historical_market import HistoricalMarketBroker

class HistoricalMarketService:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._setup_clients()
        #TODO: Add period and frequency definitions

    def _setup_clients(self):
        try:
            self.logger.info("Setting up clients")
            self.api_handler = MarketHandler()
            self.market_broker = HistoricalMarketBroker()
            self.watchlist_broker = WatchlistBroker()
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            raise

    def run(self):
        self.logger.info("Starting Historical Market Service...")
        tickers = self.watchlist_broker.get_watchlist()
        for ticker in tickers:
            self.logger.info(f"Getting historical data for: {ticker}")
            self.market_broker.set_historical(ticker=ticker, data=self.api_handler.get_price_history(ticker))

        return 0

def main():
    """Entry point for running the Historical Market Service."""
    try:
        service = HistoricalMarketService()
        result = service.run()
        # Check redis store
        data = service.market_broker.get_historical('SPY')
        df = pd.DataFrame(data)
        print(df)
        print(f"Successfully processed tickers")
        return result
    except Exception as e:
        print(f"Service failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
