import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from infrastructure.clients.grafana_client import BaseGrafanaClient
from infrastructure.logging.logger import get_logger


class AlgoTraderGrafanaClient(BaseGrafanaClient):
    """
    Grafana client for the algo_trader system.
    
    Provides InfluxDB datasource and market data dashboard configuration
    for visualizing historical market data with OHLC candlestick charts.
    """
    
    def __init__(self, auto_start: bool = False):
        """
        Initialize AlgoTrader Grafana client.
        
        Arguments:
            auto_start: If True, automatically ensure container is running and authenticate.
                       If False, only initialize configuration (for container management).
        
        Reads InfluxDB connection parameters from environment variables:
        - INFLUXDB3_HTTP_BIND_ADDR: InfluxDB server address
        - INFLUXDB3_AUTH_TOKEN: InfluxDB authentication token
        """
        super().__init__(auto_start=auto_start)
        self.logger = get_logger(self.__class__.__name__)
        
        # Load InfluxDB connection details
        self.influxdb_host = os.getenv("INFLUXDB3_HTTP_BIND_ADDR", "localhost:8181")
        self.influxdb_token = os.getenv("INFLUXDB3_AUTH_TOKEN", "")
        self.influxdb_database = "historical-market-data"
        
        # Ensure InfluxDB host has protocol
        if not self.influxdb_host.startswith(('http://', 'https://')):
            self.influxdb_host = f"http://{self.influxdb_host}"
    
    def get_datasources(self) -> List[Dict[str, Any]]:
        """
        Define InfluxDB datasource for market data.
        
        Returns:
            List containing InfluxDB datasource configuration for InfluxDB 3.0
        """
        return [
            {
                "name": "InfluxDB-MarketData",
                "type": "influxdb",
                "url": self.influxdb_host,
                "access": "proxy",
                "isDefault": True,
                "jsonData": {
                    "version": "Flux",
                    "organization": "",
                    "defaultBucket": self.influxdb_database,
                    "tlsSkipVerify": True,
                    "httpMode": "GET"
                },
                "secureJsonData": {
                    "token": self.influxdb_token
                }
            }
        ]
    
    def get_dashboards(self) -> List[Dict[str, Any]]:
        """
        Load dashboard definitions from JSON files in the grafana directory.
        
        Returns:
            List of dashboard configurations loaded from JSON files
        """
        dashboards = []
        
        # Find grafana directory relative to this file
        # This file is in system/algo_trader/clients/
        # Grafana dir is in system/algo_trader/grafana/
        current_dir = Path(__file__).parent
        grafana_dir = current_dir.parent / "grafana"
        
        if not grafana_dir.exists():
            self.logger.warning(f"Grafana directory not found: {grafana_dir}")
            return []
        
        # Load all .json files from grafana directory
        for json_file in grafana_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    dashboard_config = json.load(f)
                    dashboards.append(dashboard_config)
                    self.logger.info(f"Loaded dashboard from: {json_file.name}")
            except Exception as e:
                self.logger.error(f"Error loading dashboard {json_file}: {e}")
        
        return dashboards
    
    def get_dashboard_url(self) -> str:
        """
        Get URL to access the market data dashboard.
        
        Returns:
            Dashboard URL string
        """
        return f"{self.host}/d/market-data-candles/market-data-candlestick-charts"
    
    def setup_visualization(self) -> bool:
        """
        Complete setup of Grafana visualization.
        
        Provisions datasources and dashboards, then provides access URL.
        
        Returns:
            True if setup completed successfully, False otherwise
        """
        try:
            self.logger.info("Setting up Grafana visualization...")
            
            # Provision datasources
            if not self.provision_datasources():
                self.logger.error("Failed to provision datasources")
                return False
            
            # Provision dashboards
            if not self.provision_dashboards():
                self.logger.error("Failed to provision dashboards")
                return False
            
            # Provide access information
            dashboard_url = self.get_dashboard_url()
            self.logger.info(f"Grafana visualization setup complete!")
            self.logger.info(f"Access dashboard at: {dashboard_url}")
            self.logger.info(f"Grafana admin interface: {self.host}")
            self.logger.info(f"Admin credentials: {self.admin_user} / {self.admin_password}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up visualization: {e}")
            return False
    
    @staticmethod
    def print_access_info():
        """Display Grafana access information."""
        print("\n" + "="*60)
        print("Grafana is running!")
        print("="*60)
        print("URL: http://localhost:3000")
        print("Authentication: DISABLED (localhost development)")
        print("Market Data Dashboard: http://localhost:3000/d/market-data-candles")
        print("="*60 + "\n")
    
    def setup_after_start(self) -> bool:
        """
        Set up datasources and dashboards after container is started.
        
        This includes authentication and provisioning. Should be called
        after start_via_compose() succeeds.
        
        Returns:
            True if setup completed successfully, False otherwise
        """
        try:
            # Wait for Grafana to be ready (if not already)
            self._wait_for_ready()
            
            # Authenticate to get API key
            self._authenticate()
            
            # Provision datasources
            self.logger.info("Provisioning datasources...")
            if not self.provision_datasources():
                self.logger.error("Failed to provision datasources")
                return False
            
            # Provision dashboards
            self.logger.info("Provisioning dashboards...")
            if not self.provision_dashboards():
                self.logger.error("Failed to provision dashboards")
                return False
            
            self.logger.info("✓ Grafana setup complete!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during setup: {e}")
            return False
    
    @classmethod
    def cli(cls):
        """
        Command-line interface for Grafana container management.
        
        Provides start, stop, restart, status, and logs commands.
        This allows the client to be run as: bazel run //system/algo_trader/clients:grafana
        """
        # Parse command
        command = sys.argv[1] if len(sys.argv) > 1 else "start"
        
        # Show usage if invalid command
        valid_commands = ["start", "stop", "restart", "status", "logs"]
        if command not in valid_commands:
            print(f"Usage: {sys.argv[0]} {{start|stop|restart|status|logs}}")
            print("\nCommands:")
            print("  start   - Start Grafana container and provision dashboards (default)")
            print("  stop    - Stop Grafana container")
            print("  restart - Restart Grafana container and reprovision")
            print("  status  - Show Grafana container status")
            print("  logs    - Show Grafana logs (follow mode)")
            sys.exit(1)
        
        try:
            # Create client instance
            # auto_start=False prevents automatic container startup in __init__
            client = cls(auto_start=False)
            
            if command == "start":
                # Start container
                if not client.start_via_compose():
                    sys.exit(1)
                
                # Set up datasources and dashboards
                if not client.setup_after_start():
                    print("Warning: Container started but setup failed")
                    print("You may need to manually configure datasources and dashboards")
                
                cls.print_access_info()
            
            elif command == "stop":
                if not client.stop_via_compose():
                    sys.exit(1)
            
            elif command == "restart":
                # Restart container
                if not client.restart_via_compose():
                    sys.exit(1)
                
                # Re-provision everything
                if not client.setup_after_start():
                    print("Warning: Container restarted but setup failed")
                
                cls.print_access_info()
            
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
    # Allow running as: python -m system.algo_trader.clients.grafana_client
    AlgoTraderGrafanaClient.cli()
