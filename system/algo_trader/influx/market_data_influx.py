import pandas as pd

from infrastructure.influxdb.influxdb import BaseInfluxDBClient, BatchWriteConfig
from infrastructure.logging.logger import get_logger

market_write_config = BatchWriteConfig(
    batch_size=10000,
    flush_interval=10_00,
    jitter_interval=2_000,
    retry_interval=15_000,
    max_retries=5,
    max_retry_delay=30_000,
    exponential_base=2,
)


class MarketDataInflux(BaseInfluxDBClient):
    def __init__(self, database: str = "historical_market_data", write_config=market_write_config):
        super().__init__(database=database, write_config=write_config)
        self.logger = get_logger(self.__class__.__name__)

    def _format_stock_data(self, data: dict, ticker: str) -> pd.DataFrame:
        self.logger.debug(f"Formatting {ticker}")
        # TODO: datetime probably needs formatting
        df = pd.DataFrame(data)
        df = df.set_index(pd.to_datetime(df["datetime"], unit="ms", utc=True))
        df = df.drop("datetime", axis=1)
        return df

    def write(self, data: dict, ticker: str, table: str) -> bool:
        if table == "stock":
            df = self._format_stock_data(data, ticker)

        # Add ticker as a tag column
        df["ticker"] = ticker

        try:
            callback = self.client.write(
                df, data_frame_measurement_name=table, data_frame_tag_columns=["ticker"]
            )
            self.logger.debug(f"{callback}")

            return True
        except Exception as e:
            self.logger.error(f"Failed to write data for {ticker}: {e}")
            return False

    def query(self, query: str):
        self.logger.info("Getting data")
        try:
            df = self.client.query(query=query, language="sql", mode="pandas")
        except Exception as e:
            self.logger.error(f"Failed to retrieve query: {e}")
            df = False

        return df
