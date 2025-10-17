import os
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
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.database = self._get_database()
        
        # Load from environment
        self.host = os.getenv("INFLUXDB3_HTTP_BIND_ADDR", "localhost:8181")
        self.token = os.getenv("INFLUXDB3_AUTH_TOKEN", "")
        
        if not self.token:
            self.logger.warning("INFLUXDB3_AUTH_TOKEN not set in environment")
        
        self._create_client()
    
    @abstractmethod
    def _get_database(self) -> str:
        """
        Inheriting class needs to define their database name.
        
        Returns:
            Database name string
        """
        pass
    
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

