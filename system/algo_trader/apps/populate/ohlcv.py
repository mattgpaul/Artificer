import threading
import requests
from typing import Dict
from dataclasses import dataclass

from infrastructure.logging.logger import get_logger

from system.algo_trader.infra.schwab.market_handler import MarketHandler

@dataclass
class Ticker:
    symbol: str
    title: str
    cik: int

MAX_THREADS = 4

class OHLCVRunner:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.market_handler = MarketHandler()

    def _get_sec_tickers(self) -> list[str]:
        """Get SEC tickers from the SEC website."""
        url = "https://www.sec.gov/files/company_tickers.json"
        email = "company@example.com"
        headers = {
            "User-Agent": email,
        }
        self.logger.debug(f"Getting SEC tickers from {url}")
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
        except Exception as e:
            self.logger.error(f"Error getting SEC tickers: {e}")
            raise e
        
        tickers = [Ticker(
            symbol=data[symbol]['ticker'],
            title=data[symbol]['title'],
            cik=int(data[symbol]['cik_str']),
        ) for symbol in data]

        return tickers

    def _filter_bad_tickers(self) -> list[str]:
        """Filter out tickers that are not valid for OHLCV data."""
        pass

    def _log_bad_ticker(self, ticker: str) -> None:
        pass

    def _buffer_data(self) -> bool:
        """Buffer data to data layer for ingestion."""
        pass

    def get_ticker_ohlcv(self, ticker: str):
        """Get OHLCV data for a ticker."""
        self.logger.debug(f"Getting OHLCV data for {ticker}")
        data = self.market_handler.get_price_history(ticker)
        print(data)

    def main(self) -> None:
        # Get SEC tickers
        self.logger.info("Getting SEC tickers")
        tickers = self._get_sec_tickers()

        # Filter bad tickers
        self.logger.info("Filtering bad tickers")
        bad_tickers = self._filter_bad_tickers(tickers)

        # Get OHLCV data for each ticker
        self.logger.info("Getting OHLCV data for each ticker")
        for ticker in tickers:
            self.get_ticker_ohlcv(ticker)

            # Log bad tickers. need response code from market handler
            self.logger.info(f"Bad ticker: {ticker}")

        # Buffer data for ingestion
        self.logger.info("Buffering data for ingestion")
        self._buffer_data()

if __name__ == "__main__":
    runner = OHLCVRunner()
    runner.main()

