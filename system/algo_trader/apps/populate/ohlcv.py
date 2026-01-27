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
        self.logger.info(f"Getting SEC tickers from {url}")
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

if __name__ == "__main__":
    runner = OHLCVRunner()
    data = runner._get_sec_tickers()
    print(data)

