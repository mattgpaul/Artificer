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
        
        Reads configuration from environment variables with fallback:
        - System-specific (algo_trader.env) variables tried first
        - Falls back to infrastructure defaults (artificer.env)
        
        Required environment variables:
        - GRAFANA_HOST or default from artificer.env
        - GRAFANA_PORT or default from artificer.env  
        - GRAFANA_ADMIN_USER from artificer.env
        - GRAFANA_ADMIN_PASSWORD from artificer.env
        - GRAFANA_CONTAINER_NAME from artificer.env
        - ALGO_TRADER_INFLUXDB_DATABASE from algo_trader.env
        - ALGO_TRADER_INFLUXDB_DOCKER_HOST from algo_trader.env
        
        Arguments:
            auto_start: If True, automatically ensure container is running and authenticate.
                       If False, only initialize configuration (for container management).
        """
        # Load Grafana configuration (system-specific → artificer.env fallback)
        grafana_host = os.getenv("ALGO_TRADER_GRAFANA_HOST", os.getenv("GRAFANA_HOST", "localhost"))
        grafana_port_str = os.getenv("GRAFANA_PORT", "3000")
        grafana_port = int(grafana_port_str.split(':')[-1]) if ':' in grafana_port_str else int(grafana_port_str)
        admin_user = os.getenv("GRAFANA_ADMIN_USER", "admin")
        admin_password = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")
        container_name = os.getenv("GRAFANA_CONTAINER_NAME", "algo-trader-grafana")
        
        # Initialize base class with all configuration
        super().__init__(
            host=grafana_host,
            port=grafana_port,
            admin_user=admin_user,
            admin_password=admin_password,
            container_name=container_name,
            auto_start=auto_start
        )
        
        self.logger = get_logger(self.__class__.__name__)
        
        # Load system-specific InfluxDB connection details for datasources
        self.influxdb_docker_host = os.getenv("ALGO_TRADER_INFLUXDB_DOCKER_HOST", "influxdb:8181")
        self.influxdb_token = os.getenv("INFLUXDB3_AUTH_TOKEN", "")
        self.influxdb_database = os.getenv("ALGO_TRADER_INFLUXDB_DATABASE", "algo-trader-database")
    
    def get_datasources(self) -> List[Dict[str, Any]]:
        """
        Define InfluxDB datasource for market data.
        
        Uses Docker network hostname for container-to-container communication.
        The URL is configured via ALGO_TRADER_INFLUXDB_DOCKER_HOST environment variable.
        
        Returns:
            List containing InfluxDB datasource configuration for InfluxDB 3.0
        """
        # Ensure protocol prefix
        influxdb_url = self.influxdb_docker_host
        if not influxdb_url.startswith(('http://', 'https://')):
            influxdb_url = f"http://{influxdb_url}"
        
        return [
            {
                "name": "InfluxDB-MarketData",
                "type": "influxdb",
                "url": influxdb_url,
                "access": "proxy",
                "isDefault": True,
                "jsonData": {
                    "version": "SQL",  # InfluxDB 3.0 uses SQL via FlightSQL (gRPC)
                    "organization": "",
                    "defaultBucket": self.influxdb_database,
                    "tlsSkipVerify": True,
                    "httpMode": "GET",
                    "secureGrpc": False,  # InfluxDB 3.0 running without TLS (--without-auth)
                    "allowInsecureGrpc": True  # Allow insecure gRPC connections
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
