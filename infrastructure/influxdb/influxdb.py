import os
from abc import abstractmethod
from dataclasses import dataclass

import requests
from influxdb_client_3 import (
    InfluxDBClient3,
    InfluxDBError,
    WriteOptions,
    write_client_options,
)

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
            exponential_base=self.exponential_base,
        )


class BatchingCallback:
    def success(self, conf, data: str):
        print(f"Written batch: {conf}")

    def error(self, conf, data: str, exception: InfluxDBError):
        print(f"Cannot write batch: {conf}, data: {data} due: {exception}")

    def retry(self, conf, data: str, exception: InfluxDBError):
        print(f"Retryable error occurs for batch: {conf}, data: {data} retry: {exception}")


class BaseInfluxDBClient(Client):
    def __init__(self, database: str, write_config: BatchWriteConfig | None = None):
        self.logger = get_logger(self.__class__.__name__)

        # Read configuration from environment variables
        self.token = os.getenv("INFLUXDB3_AUTH_TOKEN", "my-secret-token")
        self.url = f"http://{os.getenv('INFLUXDB3_HTTP_BIND_ADDR', 'localhost:8181')}"
        self.database = database

        # Use provided config or default
        self.write_config = write_config or self._get_write_config()
        self._write_options = self.write_config._to_write_options()
        self._callback = BatchingCallback()
        self._wco = write_client_options(
            success_callback=self._callback.success,
            error_callback=self._callback.error,
            retry_callback=self._callback.retry,
            write_options=self._write_options,
        )

        # Create client - assumes server is already running
        self.client = InfluxDBClient3(
            token=self.token,
            host=self.url,
            database=self.database,
            write_client_options=self._wco,
        )

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
        }

    def _get_write_config(self) -> BatchWriteConfig:
        """Get write configuration - can be overridden for testing"""
        return BatchWriteConfig()

    def ping(self) -> bool:
        """Test connection to InfluxDB server"""
        try:
            response = requests.get(f"{self.url}/health", headers=self._headers)
            if response.status_code == 200:
                self.logger.debug("InfluxDB ping successful")
                return True
            else:
                self.logger.debug(f"InfluxDB ping failed with status: {response.status_code}")
                return False
        except Exception as e:
            self.logger.debug(f"InfluxDB ping failed with exception: {e}")
            return False

    def close(self):
        """Close the client and flush any pending writes"""
        if hasattr(self, "client") and self.client:
            try:
                self.client.close()
            except Exception as e:
                self.logger.warning(f"Error closing InfluxDB client: {e}")

    @abstractmethod
    def write(self):
        pass

    @abstractmethod
    def query(self):
        pass


if __name__ == "__main__":
    print(os.getenv("INFLUXDB3_AUTH_TOKEN"))
    print(os.getenv("INFLUXDB3_HTTP_BIND_ADDR"))
