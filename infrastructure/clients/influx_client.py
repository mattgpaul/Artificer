from dataclasses import dataclass
import pandas as pd
import os
import dotenv
from datetime import datetime, timezone
from typing import Any

from influxdb_client_3 import InfluxDBClient3, Point, WriteOptions, InfluxDBError, write_client_options

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger

@dataclass
class BatchWriteConfig:
    batch_size: int = 100
    flush_interval: int = 10_000
    jitter_interval: int = 2_000
    retry_interval: int = 5_000
    max_retries: int = 5
    max_retry_delay: int = 30_000
    exponential_base: int = 2

    def __post_init__(self):
        """Validate configuration values"""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")

    def _to_write_options(self):
        """Convert to format expected by InfluxDB client"""
        return WriteOptions(
            batch_size=self.batch_size,
            flush_interval=self.flush_interval,
            jitter_interval=self.jitter_interval,
            retry_interval=self.retry_interval,
            max_retries=self.max_retries,
            max_retry_delay=self.max_retry_delay,
            exponential_base=self.exponential_base
        )

class BatchingCallback(object):

    def success(self, conf, data: str):
        print(f"Written batch: {conf}")

    def error(self, conf, data: str, exception: InfluxDBError):
        print(f"Cannot write batch: {conf}, data: {data} due: {exception}")

    def retry(self, conf, data: str, exception: InfluxDBError):
        print(f"Retryable error occurs for batch: {conf}, data: {data} retry: {exception}")


class BaseInfluxDBClient(Client):
    def __init__(self, database: str):
        self.logger = get_logger(self.__class__.__name__)
        dotenv.load_dotenv(dotenv.find_dotenv("artificer.env"))
        self.token = os.getenv("INFLUXDB_TOKEN")
        self.host = "localhost"
        self.port = 8181
        self.url = f"http://{self.host}:{self.port}"
        self.database = database
        self.client = self._create_client()
        self.write_config = self._get_write_config()
        self.__write_options = self.write_config._to_write_options()
        self._callback = BatchingCallback()
        self._wco = write_client_options(
            success_callback=self._callback.success,
            error_callback=self._callback.error,
            retry_callback=self._callback.retry,
            write_options=self.__write_options
        )

    def _create_client(self):
        self.logger.info("Setting up influx client")
        client = InfluxDBClient3(
            token=self.token,
            host=self.url,
            database=self.database,
        )
        return client

    def _get_write_config(self) -> BatchWriteConfig:
        return BatchWriteConfig()

    def write_point(
        self,
        data: Any,
        name: str,
        tags: dict[str, str] = None
    ) -> bool:
        self.logger.info(f"Writing data point to {name}")
        point = Point("measurement")
        
        # Add tags if provided - following InfluxDB documentation pattern
        if tags:
            for key, value in tags.items():
                point = point.tag(key, value)
                
        point = point.field(name, data)
        try:
            self.client.write(point)
        except Exception as e:
            self.logger.error(f"Failed to write point to database: {e}")

    def write_batch(
        self,
        data: pd.DataFrame,
        name: str,
        tags: list[str],
    ) -> bool:
        self.logger.info(f"writing batch to: {self.database}")
        try:
            self.client.write(data, data_frame_measurement_name=name, data_frame_gat_colums=tags)
            return True
        except Exception as e:
            self.logger.error(f"Error writing batch to database: {e}")
            return False

    # Assume pandas only for now
    def query_data(
        self,
        query: str,
        language: str = "sql",
        mode: str = "pandas",
    ) -> pd.DataFrame:
        self.logger.info(f"Querying data from: {self.database}")
        try:
            data = self.client.query(query, language, mode)
            return data
        except Exception as e:
            self.logger.error(f"Failed to query database: {e}")
            return None

    def delete_data(self) -> bool:
        pass

    def ping(self) -> bool:
        pass

    def health_check(self) -> bool:
        pass

    def close(self):
        pass

if __name__ == "__main__":
    influx = BaseInfluxDBClient(database="test")
    influx._create_client()
    print(f"created client: {influx.client}")
    print(f"batch write config: {influx.write_config}")
    