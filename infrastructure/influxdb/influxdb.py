"""InfluxDB client and configuration for time-series data storage.

This module provides InfluxDB client functionality with batch write support,
custom error handling, and configuration management for storing market data
and other time-series metrics.
"""

import os
import threading
import time
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
    batch write operations. Tracks pending batches for graceful shutdown.
    """

    def __init__(self):
        """Initialize callback with logger and batch tracking."""
        self.logger = get_logger(self.__class__.__name__)
        self._pending_batches = 0
        self._lock = threading.Lock()

    def increment_pending(self) -> None:
        """Increment the pending batch counter (called before write)."""
        with self._lock:
            self._pending_batches += 1

    def get_pending_count(self) -> int:
        """Get the current number of pending batches."""
        with self._lock:
            return self._pending_batches

    def success(self, conf: str, data: str) -> None:
        """Handle successful batch write.

        Args:
            conf: Write configuration details.
            data: Data that was successfully written.
        """
        with self._lock:
            self._pending_batches -= 1
        self.logger.debug(f"Written batch: {conf}, pending: {self._pending_batches}")

    def error(self, conf: str, data: str, exception: InfluxDBError) -> None:
        """Handle batch write error.

        Args:
            conf: Write configuration details.
            data: Data that failed to write (can be str or bytes).
            exception: InfluxDB error that occurred.
        """
        # Decrement pending count - batch is complete (even though it failed)
        with self._lock:
            self._pending_batches -= 1

        # Convert bytes to string if needed, then truncate to avoid massive log output
        try:
            data_str = data.decode("utf-8") if isinstance(data, bytes) else data
            data_preview = data_str[:200] + "..." if len(data_str) > 200 else data_str
        except Exception:
            data_preview = "<unable to decode data>"
        self.logger.error(
            f"Cannot write batch: {conf}, data preview: {data_preview} due: {exception}, "
            f"pending: {self._pending_batches}"
        )

    def retry(self, conf: str, data: str, exception: InfluxDBError) -> None:
        """Handle retryable batch write error.

        Args:
            conf: Write configuration details.
            data: Data that will be retried (can be str or bytes).
            exception: InfluxDB error that triggered the retry.
        """
        # Note: We don't decrement here because retry means the batch will be attempted again
        # Convert bytes to string if needed, then truncate to avoid massive log output
        try:
            data_str = data.decode("utf-8") if isinstance(data, bytes) else data
            data_preview = data_str[:200] + "..." if len(data_str) > 200 else data_str
        except Exception:
            data_preview = "<unable to decode data>"
        self.logger.warning(
            f"Retryable error occurs for batch: {conf}, "
            f"data preview: {data_preview} retry: {exception}, "
            f"pending: {self._pending_batches}"
        )


class BaseInfluxDBClient(Client):
    """Base class for InfluxDB 3.0 client operations.

    Provides connection management, batch writing capabilities, and query
    operations for InfluxDB 3.0 using the Core API. This abstract base class
    handles authentication, write configuration, and connection pooling.

    Attributes:
        logger: Configured logger instance.
        token: InfluxDB authentication token from environment.
        url: InfluxDB server URL from environment.
        database: Target database name.
        write_config: Batch write configuration settings.
        client: InfluxDB client instance.
    """

    def __init__(self, database: str, write_config: BatchWriteConfig | None = None, config=None):
        """Initialize InfluxDB client with connection and write configuration.

        Args:
            database: Target database name for operations.
            write_config: Optional batch write configuration. If None, uses defaults.
            config: Optional InfluxDBConfig object. If None, auto-populates from environment.
        """
        self.logger = get_logger(self.__class__.__name__)

        # Auto-populate from environment if not provided (handles INFLUXDB3_HTTP_BUD_ADDR format)
        if config is None:
            from infrastructure.config import InfluxDBConfig  # noqa: PLC0415

            config = InfluxDBConfig.from_env()

        # Use config values (either provided or from environment)
        self.token = config.token
        self.url = f"http://{config.host}:{config.port}"
        self.database = database

        # Use provided write config or default
        self.write_config = write_config or self._get_write_config()
        self._write_options = self.write_config._to_write_options()
        self._callback = BatchingCallback()
        self._wco = write_client_options(
            success_callback=self._callback.success,
            error_callback=self._callback.error,
            retry_callback=self._callback.retry,
            write_options=self._write_options,
        )

        # Create client
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

    def wait_for_batches(self, timeout: int = 30, poll_interval: float = 0.5) -> bool:
        """Wait for all pending batch writes to complete.

        Polls the batch callback's pending counter until it reaches zero or timeout occurs.

        Args:
            timeout: Maximum time to wait in seconds (default: 30).
            poll_interval: Time between polls in seconds (default: 0.5).

        Returns:
            True if all batches completed, False if timeout occurred.
        """
        start_time = time.time()
        last_log_time = start_time

        while True:
            pending = self._callback.get_pending_count()

            if pending == 0:
                self.logger.info("All batch writes completed successfully")
                return True

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                self.logger.warning(
                    f"Timeout waiting for batches to complete. "
                    f"{pending} batches still pending after {timeout}s"
                )
                return False

            # Log progress every 5 seconds
            if time.time() - last_log_time >= 5:
                self.logger.info(f"Waiting for {pending} pending batches to complete...")
                last_log_time = time.time()

            time.sleep(poll_interval)

    def close(self):
        """Close the client and flush any pending writes."""
        if hasattr(self, "client") and self.client:
            try:
                self.client.close()
            except Exception as e:
                self.logger.warning(f"Error closing InfluxDB client: {e}")

    @abstractmethod
    def write(self):
        """Write data to InfluxDB.

        Subclasses must implement this method to define how data is formatted
        and written to InfluxDB.
        """
        pass

    @abstractmethod
    def query(self):
        """Query data from InfluxDB.

        Subclasses must implement this method to define how data is queried
        from InfluxDB.
        """
        pass


if __name__ == "__main__":
    print(os.getenv("INFLUXDB3_AUTH_TOKEN"))
    print(os.getenv("INFLUXDB3_HTTP_BIND_ADDR"))
