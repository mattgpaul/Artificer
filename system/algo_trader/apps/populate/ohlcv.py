import threading
from typing import Dict

from infrastructure.logging.logger import get_logger

from system.algo_trader.infra.schwab.market_handler import MarketHandler

class OHLCVRunner:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.market_handler = MarketHandler()

    def _get_sec_tickers(self) -> list[str]:
        """Get SEC tickers from the SEC website."""
        pass

    def _filter_bad_tickers(self) -> list[str]:
        """Filter out tickers that are not valid for OHLCV data."""
        pass

    def _buffer_data(self) -> bool:
        """Buffer data to data layer for ingestion."""
        pass

    def get_ticker_ohlcv(self, ticker: str):
        """Get OHLCV data for a ticker."""
        data = self.market_handler.get_price_history(ticker)
        print(data)

if __name__ == "__main__":
    runner = OHLCVRunner()
    runner.get_ticker_ohlcv("AAPL")

