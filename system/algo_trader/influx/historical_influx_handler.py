import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Union, List

from infrastructure.clients.influx_client import BaseInfluxDBClient

from infrastructure.logging.logger import get_logger

class HistoricalInfluxHandler(BaseInfluxDBClient):
    def __init__(self, database: str = "historical_market_data"):
        super().__init__(database=database)
        self.logger = get_logger(self.__class__.__name__)

    def _format_stock_data(self, data: dict, ticker: str) -> pd.DataFrame:
        self.logger.debug(f"Formatting {ticker}")
        #TODO: datetime probably needs formatting
        df = pd.DataFrame(data)
        df = df.set_index(pd.to_datetime(df['datetime'], unit='ms', utc=True))
        df = df.drop('datetime', axis=1)
        return df


    def write(self, data: dict, ticker: str, table: str) -> bool:
        if table == "stock":
            df = self._format_stock_data(data, ticker)
            
        # Add ticker as a tag column
        df['ticker'] = ticker
        
        try:
            self.client.write(
                df, 
                data_frame_measurement_name=table,
                data_frame_tag_columns=["ticker"]
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to write data for {ticker}: {e}")
            return False
        

    def query(self):
        pass
    