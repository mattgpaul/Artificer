import pandas as pd

from infrastructure.clients.influx_client import BaseInfluxDBClient

from infrastructure.logging.logger import get_logger

class HistoricalInfluxHandler(BaseInfluxDBClient):
    def __init__(self, database: str = "historical_market_data"):
        super().__init__(database=database)
        self.logger = get_logger(self.__class__.__name__)

    def write_historical_data(self, ticker: str, data: list[dict], tags: list[str]) -> bool:
        self.logger.info(f"Writing historical data for {ticker}")
        data = pd.DataFrame(data)
        success = self.write_batch(data, ticker, tags)
        if not success:
            self.logger.error(f"Failed to write historical data for {ticker}")
        return success

    def query_historical_data(self, ticker: str, tags: list[str]) -> pd.DataFrame:
        pass

