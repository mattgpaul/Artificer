# Get everything under the sun and write it to the database
# Probably need threading at some point to speed this up
import requests
import time

from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.redis.historical_market import HistoricalMarketBroker
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType

from infrastructure.clients.influx_client import BatchWriteConfig
from infrastructure.logging.logger import get_logger

populate_config = BatchWriteConfig(
    batch_size=10000,  
    flush_interval=10_000,  
    jitter_interval=20_000,
    retry_interval=5_000,
    max_retries=5,
    max_retry_delay=30_000,
    exponential_base=2
)

logger = get_logger("PopulateStock")
market_handler = MarketHandler()
influx_handler = MarketDataInflux(write_config=populate_config)
redis_handler = HistoricalMarketBroker()


def get_tickers():
    # Try redis first
    tickers = redis_handler.get_tickers()
    if tickers:
        return tickers

    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        'User-Agent': 'YourAppName your-email@domain.com',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate'
    }
    try:
        logger.info(f"Fetching ticker data from SEC")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        tickers = []
        for key, company_info in data.items():
            if 'ticker' in company_info:
                tickers.append(company_info['ticker'])

        logger.debug(f"Fetched {len(tickers)} ticker symbols")
        redis_handler.set_tickers(tickers=tickers)
        logger.debug("Set tickers to redis")
        return tickers

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch ticker data: {e}")

def get_data(ticker: str):
    data = market_handler.get_price_history(
        ticker=ticker,
        period_type=PeriodType.YEAR,
        period=20,
        frequency_type=FrequencyType.DAILY,
        frequency=1
    )
    return data

def store_data(data):
    success = influx_handler.write(
    data=data["candles"], 
    ticker=data["symbol"], 
    table="stock",
    )
    return success

def main():
    miss = []
    tickers = get_tickers()
    logger.info(f"Num tickers: {len(tickers)}")

    try:
        for symbol in tickers:
            try:
                data = get_data(symbol)
                success = store_data(data)
            except Exception as e:
                miss.append(symbol)
                continue
    finally:
        # Ensure all batch writes are completed before script exits
        time.sleep(30)
        logger.info(f"Missed tickers {miss}")
        logger.info(f"Completed processing {len(tickers)} tickers, {len(miss)} failed")

if __name__ == "__main__":
    main()
