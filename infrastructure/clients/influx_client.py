from dataclasses import dataclass
from abc import abstractmethod
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
        self.url = f"http://{os.getenv('INFLUXDB3_HTTP_BIND_ADDR')}"
        self.logger.debug(f"InfluxDB URL: {self.url}")
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
            # Start process in background - no stdout/stderr pipes, no communicate()
            subprocess.Popen([
                "influxdb3", "serve",
                "--node-id", os.getenv("INFLUXDB3_NODE_IDENTIFIER_PREFIX"),
                "--object-store", os.getenv("INFLUXDB3_OBJECT_STORE"),
                "--http-bind", os.getenv("INFLUXDB3_HTTP_BIND_ADDR"),
                "--data-dir", os.path.expanduser("~/.influxdb3/data"),
            ])
            
            # Wait for server to become ready using ping (no process communication needed)
            for attempt in range(5):  # Try for ~5 seconds
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
            write_client_options=self._wco,
        )
        self._start_server()
        return client

    def _check_database(self):
        """
        Check if database exists using REST API
        """
        try:
            # Use SHOW DATABASES to check if our database exists
            response = requests.get(
                f"{self.url}/api/v3/query_influxql",
                headers=self._headers,
                params={
                    "db": "_internal",  # Use _internal database for the query
                    "q": "SHOW DATABASES"
                }
            )

            if response.status_code == 200:
                # Parse the response to check if our database exists
                try:
                    data = response.json()
                    database_names = [item.get("iox::database") for item in data if item.get("iox::database") == self.database]
                    return len(database_names) > 0
                except (ValueError, KeyError):
                    # If we can't parse the response, assume database doesn't exist
                    return False
            else:
                # Any non-200 response means database doesn't exist or other error
                return False
        except Exception as e:
            self.logger.debug(f"Database check failed: {e}")
            return False

    def _get_write_config(self) -> BatchWriteConfig:
        return BatchWriteConfig()

    def ping(self) -> bool:
        try:
            response = requests.get(f"{self.url}/health", headers=self._headers)
            if response.status_code == 200:
                # Handle both JSON and plain text responses
                try:
                    ping_data = response.json()
                    self.logger.debug(f"InfluxDB ping successful: {ping_data.get('version', 'unknown version')}")
                except ValueError:
                    # If not JSON, just log the text response
                    self.logger.debug(f"InfluxDB ping successful: {response.text.strip()}")
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

    @abstractmethod
    def write(self):
        pass

    @abstractmethod
    def query(self):
        pass

if __name__ == "__main__":
    print(os.getenv("INFLUXDB3_AUTH_TOKEN"))
    print(os.getenv("INFLUXDB3_HTTP_BIND_ADDR"))

    