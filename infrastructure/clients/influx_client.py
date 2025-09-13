from dataclasses import dataclass
import os
import dotenv
from datetime import datetime, timezone

from influxdb_client_3 import InfluxDBClient3, Point

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
        # Add other validations


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

    def _create_client(self):
        self.logger.info("Setting up influx client")
        client = InfluxDBClient3(
            token=self.token,
            host=self.url,
            database=self.database,
        )
        return client

    def write_point(self) -> bool:
        pass

    def write_batch(self, batch_write_options: dict[str, int]) -> bool:
        pass

    def query_data(self):
        pass

    def delete_data(self) -> bool:
        pass

    def ping(self) -> bool:
        pass

    def health_check(self) -> bool:
        pass

    def close(self):
        pass

if __name__ == "__main__":
    influx = BaseInfluxDBClient()
    influx._create_client()
    print(f"created client: {influx.client}")
    