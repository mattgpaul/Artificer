import os
import sys
import subprocess
import time
import requests
from typing import Optional, Dict, Any, List
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from influxdb_client_3 import InfluxDBClient3, Point, WriteOptions
from infrastructure.logging.logger import get_logger
from infrastructure.client import Client


class BaseInfluxDBClient(Client):
    """
    Base InfluxDB client providing common functionality.
    
    Uses InfluxDB 3.0 API for time-series data storage and querying.
    Inheriting classes must define their database name via _get_database().
    """
    
    def __init__(self, host: str, port: int, database: str, token: str, 
                 container_name: str, auto_start: bool = False):
        """
        Initialize InfluxDB connection.
        
        Infrastructure layer - generic InfluxDB container management and API interaction.
        All configuration must be provided by the inheriting system-level implementation.
        
        Arguments:
            host: InfluxDB server hostname (e.g., 'localhost')
            port: InfluxDB server port (e.g., 8181)
            database: Database name to use
            token: Authentication token (empty string if auth disabled)
            container_name: Docker container name for lifecycle management
            auto_start: If True, automatically ensure container is running.
                       If False, only initialize configuration (for container management).
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        
        # Store configuration (no defaults - must be provided by caller)
        self.host = f"{host}:{port}" if ':' not in host else host
        self.database = database
        self.token = token
        self.container_name = container_name
        
        if not self.token:
            self.logger.debug("Token not provided - authentication disabled")
        
        # Only auto-start if requested
        if auto_start:
            self._ensure_container_running()
        
        self._create_client()
    
    def _is_container_running(self) -> bool:
        """
        Check if InfluxDB container is running.
        
        Returns:
            True if container is running, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return self.container_name in result.stdout
        except Exception as e:
            self.logger.debug(f"Error checking container status: {e}")
            return False
    
    def _ensure_container_running(self):
        """
        Ensure InfluxDB container is running, start it if necessary.
        
        Raises:
            RuntimeError: If container cannot be started
        """
        if self._is_container_running():
            self.logger.debug("InfluxDB container already running")
            return
        
        self.logger.info("InfluxDB container not running, attempting to start")
        if not self.start_via_compose():
            raise RuntimeError("Failed to start InfluxDB container")
    
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
            result = self.client.query(query=sql, mode="pandas")
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
    
    @staticmethod
    def find_project_root() -> Path:
        """
        Find the project root directory (where docker-compose.yml lives).
        
        Returns:
            Path to project root
            
        Raises:
            RuntimeError: If docker-compose.yml cannot be found
        """
        # Start from current file and traverse up
        current = Path(__file__).resolve().parent
        while current.parent != current:
            if (current / "docker-compose.yml").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not find docker-compose.yml in project hierarchy")
    
    @staticmethod
    def get_compose_command() -> List[str]:
        """
        Determine docker-compose command (v1 or v2).
        
        Returns:
            Command to use for docker-compose
            
        Raises:
            RuntimeError: If docker-compose is not installed
        """
        # Try docker compose v2 first
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            return ["docker", "compose"]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Fall back to docker-compose v1
        try:
            subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            return ["docker-compose"]
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("docker-compose not found. Please install Docker Compose.")
    
    def start_via_compose(self) -> bool:
        """
        Start InfluxDB container using docker-compose.
        
        Uses the project's docker-compose.yml for configuration.
        Waits for InfluxDB to be ready before returning.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            project_root = self.find_project_root()
            compose_file = project_root / "docker-compose.yml"
            compose_cmd = self.get_compose_command()
            
            if self._is_container_running():
                self.logger.info("InfluxDB is already running")
                return True
            
            self.logger.info("Starting InfluxDB container via docker-compose...")
            subprocess.run(
                [*compose_cmd, "-f", str(compose_file), "up", "-d", "influxdb"],
                cwd=project_root,
                check=True,
                timeout=60
            )
            
            # Wait for InfluxDB to be ready
            self.logger.info("Waiting for InfluxDB to be ready...")
            host_url = f"http://{self.host}" if not self.host.startswith(('http://', 'https://')) else self.host
            
            for attempt in range(30):
                try:
                    response = requests.get(f"{host_url}/health", timeout=2)
                    if response.status_code == 200:
                        self.logger.info("✓ InfluxDB is ready!")
                        return True
                except Exception:
                    pass
                time.sleep(2)
            
            self.logger.warning("InfluxDB may not be fully ready yet")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start InfluxDB: {e}")
            return False
    
    def stop_via_compose(self) -> bool:
        """
        Stop InfluxDB container using docker-compose.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            project_root = self.find_project_root()
            compose_file = project_root / "docker-compose.yml"
            compose_cmd = self.get_compose_command()
            
            if not self._is_container_running():
                self.logger.info("InfluxDB is not running")
                return True
            
            self.logger.info("Stopping InfluxDB container...")
            subprocess.run(
                [*compose_cmd, "-f", str(compose_file), "stop", "influxdb"],
                cwd=project_root,
                check=True,
                timeout=30
            )
            self.logger.info("✓ InfluxDB stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop InfluxDB: {e}")
            return False
    
    def restart_via_compose(self) -> bool:
        """
        Restart InfluxDB container using docker-compose.
        
        Returns:
            True if restarted successfully, False otherwise
        """
        self.logger.info("Restarting InfluxDB...")
        if not self.stop_via_compose():
            return False
        time.sleep(2)
        return self.start_via_compose()
    
    def status_via_compose(self):
        """Show InfluxDB container status using docker-compose."""
        try:
            project_root = self.find_project_root()
            compose_file = project_root / "docker-compose.yml"
            compose_cmd = self.get_compose_command()
            
            subprocess.run(
                [*compose_cmd, "-f", str(compose_file), "ps", "influxdb"],
                cwd=project_root
            )
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
    
    def logs_via_compose(self, follow: bool = True):
        """
        Show InfluxDB logs using docker-compose.
        
        Arguments:
            follow: Whether to follow logs (default True)
        """
        try:
            project_root = self.find_project_root()
            compose_file = project_root / "docker-compose.yml"
            compose_cmd = self.get_compose_command()
            
            cmd = [*compose_cmd, "-f", str(compose_file), "logs"]
            if follow:
                cmd.append("-f")
            cmd.append("influxdb")
            
            subprocess.run(cmd, cwd=project_root)
        except Exception as e:
            self.logger.error(f"Failed to show logs: {e}")
    
    @classmethod
    def cli(cls):
        """
        Command-line interface for InfluxDB container management.
        
        Provides start, stop, restart, status, and logs commands.
        This allows the client to be run as: bazel run //infrastructure/clients:influxdb
        """
        # Parse command
        command = sys.argv[1] if len(sys.argv) > 1 else "start"
        
        # Show usage if invalid command
        valid_commands = ["start", "stop", "restart", "status", "logs"]
        if command not in valid_commands:
            print(f"Usage: {sys.argv[0]} {{start|stop|restart|status|logs}}")
            print("\nCommands:")
            print("  start   - Start InfluxDB container (default)")
            print("  stop    - Stop InfluxDB container")
            print("  restart - Restart InfluxDB container")
            print("  status  - Show InfluxDB container status")
            print("  logs    - Show InfluxDB logs (follow mode)")
            sys.exit(1)
        
        try:
            # For CLI usage, load from environment variables
            # These should be in artificer.env as safe defaults
            host = os.getenv("INFLUXDB3_HOST", "localhost")
            port = int(os.getenv("INFLUXDB3_PORT", "8181"))
            database = "default"  # CLI doesn't need specific database
            token = os.getenv("INFLUXDB3_AUTH_TOKEN", "")
            container_name = os.getenv("INFLUXDB3_CONTAINER_NAME", "influxdb")
            
            # Create client instance (auto_start=False prevents automatic startup)
            client = cls(host=host, port=port, database=database, token=token, 
                        container_name=container_name, auto_start=False)
            
            if command == "start":
                if not client.start_via_compose():
                    sys.exit(1)
                print("\n" + "="*60)
                print("InfluxDB is running!")
                print("="*60)
                print(f"API URL: http://{client.host}")
                print("Health endpoint: /health")
                print("="*60 + "\n")
            
            elif command == "stop":
                if not client.stop_via_compose():
                    sys.exit(1)
            
            elif command == "restart":
                if not client.restart_via_compose():
                    sys.exit(1)
                print("\n" + "="*60)
                print("InfluxDB restarted!")
                print("="*60)
                print(f"API URL: http://{client.host}")
                print("="*60 + "\n")
            
            elif command == "status":
                client.status_via_compose()
            
            elif command == "logs":
                client.logs_via_compose(follow=True)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    # Allow running as: python -m infrastructure.clients.influxdb_client
    BaseInfluxDBClient.cli()

