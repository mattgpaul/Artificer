from dataclasses import dataclass
import requests
import time
import subprocess
import pandas as pd
import os
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
        
        # Read configuration from environment variables
        self.token = os.getenv("INFLUXDB3_AUTH_TOKEN")
        self.url = os.getenv("INFLUXDB3_HTTP_BIND_ADDR")
        self.database = database
        self.write_config = self._get_write_config()
        self.__write_options = self.write_config._to_write_options()
        self._callback = BatchingCallback()
        self._wco = write_client_options(
            success_callback=self._callback.success,
            error_callback=self._callback.error,
            retry_callback=self._callback.retry,
            write_options=self.__write_options
        )
        self.client = self._create_client()

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
        }

    def _start_server(self):
        active = self.ping()
        if not active:
            self.logger.warning("InfluxDB server is not active")
            self.logger.info("Starting InfluxDB server")
            subprocess.Popen([
                "influxdb3", "serve",
                "--node-id", os.getenv("INFLUXDB3_NODE_IDENTIFIER_PREFIX", "node0"),
                "--object-store", os.getenv("INFLUXDB3_OBJECT_STORE", "file"),
                "--http-bind-addr", os.getenv("INFLUXDB3_HTTP_BIND_ADDR", "http://localhost:8181"),
                "--data-dir", "~/.influxdb3/data",
            ])

            for attempt in range(10):  # Try for ~10 seconds
                time.sleep(1)
                if self.ping():
                    self.logger.info(f"Server is running at {self.url}")
                    return True
                    
            self.logger.error("Server started but never became ready")
            return False
        
        self.logger.info(f"Server is running at {self.url}")
        return True

    def _stop_server(self):
        """Stop InfluxDB server by finding and killing the process"""
        try:
            # Kill the influxdb3 serve process
            result = subprocess.run(
                ["pkill", "-f", "influxdb3 serve"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info("InfluxDB server stopped")
                return True
            else:
                self.logger.info("No InfluxDB server found running")
                return True  # Not running = mission accomplished
                
        except Exception as e:
            self.logger.error(f"Error stopping server: {e}")
            return False

    def _create_client(self):
        self.logger.info("Setting up influx client")
        client = InfluxDBClient3(
            token=self.token,
            host=self.url,
            database=self.database,
        )
        self._start_server()
        return client

    def _get_write_config(self) -> BatchWriteConfig:
        return BatchWriteConfig()

    def write_point(
        self,
        measurement: str,
        data: Any,
        name: str,
        tags: dict[str, str] = None
    ) -> bool:
        self.logger.info(f"Writing data point to {name}")
        point = Point(measurement)
        
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
        try:
            response = requests.get(f"{self.url}/health", headers=self._headers)
            if response.status_code == 200:
                ping_data = response.json()
                self.logger.debug(f"InfluxDB ping successful: {ping_data.get('version', 'unknown version')}")
                return True
            else:
                self.logger.debug(f"InfluxDB ping failed with status: {response.status_code}")
                return False
        except Exception as e:
            self.logger.debug(f"InfluxDB ping failed with exception: {e}")
            return False

    def health_check(self) -> bool:
        response = requests.get(f"{self.url}/health", headers=self._headers)
        if response.status_code == 200:
            self.logger.debug(f"InfluxDB health check successful: {response}")
            return True
        else:
            self.logger.debug(f"InfluxDB health check failed with status: {response.status_code}")
            return False

    def close(self):
        pass

if __name__ == "__main__":
    print(os.getenv("INFLUXDB3_AUTH_TOKEN"))
    print(os.getenv("INFLUXDB3_HTTP_BIND_ADDR"))

    