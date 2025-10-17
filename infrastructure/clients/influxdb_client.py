import os
import subprocess
import time
import requests
from typing import Optional, Dict, Any, List
from abc import abstractmethod
from datetime import datetime
from influxdb_client_3 import InfluxDBClient3, Point, WriteOptions
from infrastructure.logging.logger import get_logger
from infrastructure.client import Client


class BaseInfluxDBClient(Client):
    """
    Base InfluxDB client providing common functionality.
    
    Uses InfluxDB 3.0 API for time-series data storage and querying.
    Inheriting classes must define their database name via _get_database().
    """
    
    def __init__(self):
        """
        Initialize InfluxDB connection.
        
        Reads connection parameters from environment variables:
        - INFLUXDB3_HTTP_BIND_ADDR: InfluxDB server address
        - INFLUXDB3_AUTH_TOKEN: Authentication token
        - INFLUXDB3_NODE_IDENTIFIER_PREFIX: Node ID for server
        - INFLUXDB3_OBJECT_STORE: Object store type (file, s3, etc.)
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.database = self._get_database()
        
        # Load from environment
        self.host = os.getenv("INFLUXDB3_HTTP_BIND_ADDR", "localhost:8181")
        self.token = os.getenv("INFLUXDB3_AUTH_TOKEN", "")
        self.node_id = os.getenv("INFLUXDB3_NODE_IDENTIFIER_PREFIX", "node0")
        self.object_store = os.getenv("INFLUXDB3_OBJECT_STORE", "file")
        
        if not self.token:
            self.logger.warning("INFLUXDB3_AUTH_TOKEN not set in environment")
        
        # Ensure InfluxDB server is running
        self._ensure_server_running()
        
        self._create_client()
    
    @abstractmethod
    def _get_database(self) -> str:
        """
        Inheriting class needs to define their database name.
        
        Returns:
            Database name string
        """
        pass
    
    def _is_server_running(self) -> bool:
        """
        Check if InfluxDB server is running by pinging the health endpoint.
        
        Returns:
            True if server is responsive, False otherwise
        """
        try:
            host_url = f"http://{self.host}" if not self.host.startswith(('http://', 'https://')) else self.host
            response = requests.get(f"{host_url}/health", timeout=2)
            if response.status_code == 200:
                self.logger.debug("InfluxDB server is running")
                return True
            return False
        except Exception as e:
            self.logger.debug(f"InfluxDB server not responding: {e}")
            return False
    
    def _start_server(self) -> bool:
        """
        Start the InfluxDB3 server in the background.
        
        Returns:
            True if server started successfully, False otherwise
        """
        try:
            influxdb3_binary = os.path.expanduser("~/.influxdb/influxdb3")
            
            if not os.path.exists(influxdb3_binary):
                self.logger.error(f"InfluxDB3 binary not found at {influxdb3_binary}")
                return False
            
            # Build command to start server
            data_dir = os.path.expanduser("~/.influxdb3_data")
            cmd = [
                influxdb3_binary,
                "serve",
                "--node-id", self.node_id,
                "--object-store", self.object_store,
                "--http-bind", self.host,
                "--data-dir", data_dir,
                "--without-auth"  # Using without-auth for now since we have token in env
            ]
            
            self.logger.info(f"Starting InfluxDB3 server on {self.host}")
            
            # Start server in background
            log_file = open("/tmp/influxdb3.log", "a")
            subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
            
            # Wait for server to start (up to 10 seconds)
            for i in range(10):
                time.sleep(1)
                if self._is_server_running():
                    self.logger.info("InfluxDB3 server started successfully")
                    return True
            
            self.logger.error("InfluxDB3 server failed to start within timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Error starting InfluxDB server: {e}")
            return False
    
    def _ensure_server_running(self):
        """
        Ensure InfluxDB server is running, start it if necessary.
        
        Raises:
            RuntimeError: If server cannot be started
        """
        if self._is_server_running():
            self.logger.debug("InfluxDB server already running")
            return
        
        self.logger.info("InfluxDB server not running, attempting to start")
        if not self._start_server():
            raise RuntimeError("Failed to start InfluxDB server")
    
    def _create_client(self):
        """Create InfluxDB client connection."""
        try:
            # Format: "https://host:port" or just "host:port" for HTTP
            host_url = f"http://{self.host}" if not self.host.startswith(('http://', 'https://')) else self.host
            
            self.client = InfluxDBClient3(
                host=host_url,
                token=self.token,
                database=self.database
            )
            self.logger.info(f"InfluxDB client created for database '{self.database}'")
        except Exception as e:
            self.logger.error(f"Failed to create InfluxDB client: {e}")
            raise
    
    def write_point(self, measurement: str, tags: Dict[str, str], 
                    fields: Dict[str, Any], timestamp: Optional[datetime] = None) -> bool:
        """
        Write a single data point to InfluxDB.
        
        Arguments:
            measurement: Measurement name (similar to table name)
            tags: Dictionary of tag key-value pairs (indexed, for filtering)
            fields: Dictionary of field key-value pairs (actual data)
            timestamp: Optional timestamp (defaults to current time)
            
        Returns:
            True if write successful, False otherwise
        """
        try:
            self.logger.debug(f"Writing point to measurement '{measurement}'")
            point = Point(measurement)
            
            # Add tags
            for tag_key, tag_value in tags.items():
                point = point.tag(tag_key, tag_value)
            
            # Add fields
            for field_key, field_value in fields.items():
                point = point.field(field_key, field_value)
            
            # Set timestamp if provided
            if timestamp:
                point = point.time(timestamp)
            
            self.client.write(record=point)
            self.logger.debug(f"Successfully wrote point to '{measurement}'")
            return True
        except Exception as e:
            self.logger.error(f"Error writing point to '{measurement}': {e}")
            return False
    
    def write_points(self, points: List[Point], batch_size: Optional[int] = None) -> bool:
        """
        Write multiple data points to InfluxDB in a batch.
        
        Arguments:
            points: List of Point objects to write
            batch_size: Optional batch size (None writes all at once)
            
        Returns:
            True if all writes successful, False if any failed
        """
        try:
            self.logger.debug(f"Writing {len(points)} points in batch")
            
            # Write all points at once if no batch size specified
            if batch_size is None or batch_size >= len(points):
                self.client.write(record=points)
                self.logger.info(f"Successfully wrote {len(points)} points")
                return True
            
            # Otherwise write in batches
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.write(record=batch)
                self.logger.debug(f"Wrote batch {i // batch_size + 1}")
            
            self.logger.info(f"Successfully wrote {len(points)} points in batches")
            return True
        except Exception as e:
            self.logger.error(f"Error writing points in batch: {e}")
            return False
    
    def query(self, sql: str) -> Optional[Any]:
        """
        Execute SQL query against InfluxDB.
        
        Arguments:
            sql: SQL query string
            
        Returns:
            Query results as pandas DataFrame if successful, None otherwise
        """
        try:
            self.logger.debug(f"Executing query: {sql[:100]}...")
            result = self.client.query(query=sql)
            self.logger.debug(f"Query executed successfully, returned {len(result)} rows")
            return result
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            return None
    
    def close(self):
        """Close InfluxDB client connection."""
        try:
            if hasattr(self, 'client') and self.client:
                self.client.close()
                self.logger.info("InfluxDB client connection closed")
        except Exception as e:
            self.logger.error(f"Error closing InfluxDB client: {e}")

