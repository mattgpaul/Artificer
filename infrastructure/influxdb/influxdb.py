"""InfluxDB client and configuration for time-series data storage.

This module provides InfluxDB client functionality with batch write support,
custom error handling, and configuration management for storing market data
and other time-series metrics.
"""

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
    """Configuration for InfluxDB batch write operations.

    Defines parameters for batching, flushing, and retry behavior when
    writing data to InfluxDB.

    Attributes:
        batch_size: Number of records to batch before writing.
        flush_interval: Milliseconds between automatic flushes.
        jitter_interval: Random jitter added to flush interval in milliseconds.
        retry_interval: Milliseconds to wait between retries.
        max_retries: Maximum number of retry attempts.
        max_retry_delay: Maximum retry delay in milliseconds.
        exponential_base: Base for exponential backoff calculation.
    """

    batch_size: int = 100
    flush_interval: int = 10_000
    jitter_interval: int = 2_000
    retry_interval: int = 5_000
    max_retries: int = 5
    max_retry_delay: int = 30_000
    exponential_base: int = 2

    def __post_init__(self) -> None:
        """Validate configuration values after initialization.

        Raises:
            ValueError: If batch_size is non-positive or max_retries is negative.
        """
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")

    def _to_write_options(self) -> WriteOptions:
        """Convert configuration to InfluxDB WriteOptions format.

        Returns:
            WriteOptions instance with configured batch write parameters.
        """
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
    """Callback handler for InfluxDB batch write operations.

    Provides success, error, and retry callback methods for monitoring
    batch write operations.
    """

    def success(self, conf: str, data: str) -> None:
        """Handle successful batch write.

        Args:
            conf: Write configuration details.
            data: Data that was successfully written.
        """
        print(f"Written batch: {conf}")

    def error(self, conf: str, data: str, exception: InfluxDBError) -> None:
        """Handle batch write error.

        Args:
            conf: Write configuration details.
            data: Data that failed to write.
            exception: InfluxDB error that occurred.
        """
        print(f"Cannot write batch: {conf}, data: {data} due: {exception}")

    def retry(self, conf: str, data: str, exception: InfluxDBError) -> None:
        """Handle retryable batch write error.

        Args:
            conf: Write configuration details.
            data: Data that will be retried.
            exception: InfluxDB error that triggered the retry.
        """
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
        """Get write configuration - can be overridden for testing."""
        return BatchWriteConfig()

    def ping(self) -> bool:
        """Test connection to InfluxDB server."""
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
        """Close the client and flush any pending writes."""
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
