import os
import sys
import time
import requests
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from abc import abstractmethod
from infrastructure.logging.logger import get_logger
from infrastructure.client import Client


class BaseGrafanaClient(Client):
    """
    Base Grafana client providing full lifecycle management.
    
    Handles container management, datasource provisioning, and dashboard management.
    Inheriting classes must define their Grafana configuration via abstract methods.
    """
    
    def __init__(self, auto_start: bool = False):
        """
        Initialize Grafana client.
        
        Arguments:
            auto_start: If True, automatically ensure container is running and authenticate.
                       If False, only initialize configuration (for container management).
        
        Reads connection parameters from environment variables:
        - GRAFANA_HOST: Grafana server address (default: localhost:3000)
        - GRAFANA_ADMIN_USER: Admin username (default: admin)
        - GRAFANA_ADMIN_PASSWORD: Admin password (default: admin)
        - GRAFANA_CONTAINER_NAME: Container name (default: algo-trader-grafana)
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        
        # Load from environment
        self.host = os.getenv("GRAFANA_HOST", "localhost:3000")
        self.admin_user = os.getenv("GRAFANA_ADMIN_USER", "admin")
        self.admin_password = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")
        self.container_name = os.getenv("GRAFANA_CONTAINER_NAME", "algo-trader-grafana")
        
        # Ensure host has protocol
        if not self.host.startswith(('http://', 'https://')):
            self.host = f"http://{self.host}"
        
        self.api_key = None
        
        # Only auto-start and authenticate if requested
        # For container lifecycle management, we don't need this
        if auto_start:
            self._ensure_container_running()
            self._wait_for_ready()
            self._authenticate()
    
    @abstractmethod
    def get_datasources(self) -> List[Dict[str, Any]]:
        """
        Inheriting class must define datasources to provision.
        
        Returns:
            List of datasource configurations
        """
        pass
    
    @abstractmethod
    def get_dashboards(self) -> List[Dict[str, Any]]:
        """
        Inheriting class must define dashboards to provision.
        
        Returns:
            List of dashboard configurations
        """
        pass
    
    def _is_container_running(self) -> bool:
        """
        Check if Grafana container is running.
        
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
    
    def _start_container(self) -> bool:
        """
        Start Grafana container.
        
        Returns:
            True if container started successfully, False otherwise
        """
        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if self.container_name in result.stdout:
                # Container exists, start it
                subprocess.run(
                    ["docker", "start", self.container_name],
                    check=True,
                    timeout=10
                )
                self.logger.info(f"Started existing Grafana container: {self.container_name}")
            else:
                # Create and start new container
                cmd = [
                    "docker", "run", "-d",
                    "--name", self.container_name,
                    "-p", "3000:3000",
                    "-e", f"GF_SECURITY_ADMIN_USER={self.admin_user}",
                    "-e", f"GF_SECURITY_ADMIN_PASSWORD={self.admin_password}",
                    "grafana/grafana:latest"
                ]
                
                subprocess.run(cmd, check=True, timeout=30)
                self.logger.info(f"Created and started new Grafana container: {self.container_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Grafana container: {e}")
            return False
    
    def _ensure_container_running(self):
        """
        Ensure Grafana container is running, start it if necessary.
        
        Raises:
            RuntimeError: If container cannot be started
        """
        if self._is_container_running():
            self.logger.debug("Grafana container already running")
            return
        
        self.logger.info("Grafana container not running, attempting to start")
        if not self._start_container():
            raise RuntimeError("Failed to start Grafana container")
    
    def _wait_for_ready(self, timeout: int = 60):
        """
        Wait for Grafana to be ready to accept requests.
        
        Arguments:
            timeout: Maximum time to wait in seconds
            
        Raises:
            RuntimeError: If Grafana doesn't become ready within timeout
        """
        self.logger.info("Waiting for Grafana to be ready...")
        
        for i in range(timeout):
            try:
                response = requests.get(f"{self.host}/api/health", timeout=2)
                if response.status_code == 200:
                    self.logger.info("Grafana is ready")
                    return
            except Exception:
                pass
            
            time.sleep(1)
        
        raise RuntimeError(f"Grafana did not become ready within {timeout} seconds")
    
    def _authenticate(self):
        """
        Authenticate with Grafana and get API key.
        
        If anonymous auth is enabled, sets api_key to None (not needed).
        
        Raises:
            RuntimeError: If authentication fails
        """
        try:
            # Check if anonymous auth is enabled by testing API access without auth
            test_response = requests.get(f"{self.host}/api/org", timeout=5)
            
            if test_response.status_code == 200:
                # Anonymous auth is enabled, no API key needed
                self.api_key = None
                self.logger.info("Grafana anonymous auth enabled - no API key needed")
                return
            
            # Anonymous auth not enabled, need to create API key
            # Try to get existing API key first
            response = requests.get(
                f"{self.host}/api/auth/keys",
                auth=(self.admin_user, self.admin_password),
                timeout=10
            )
            
            if response.status_code == 200:
                keys = response.json()
                # Look for existing key
                for key in keys:
                    if key.get('name') == 'algo_trader_api_key':
                        self.api_key = key['key']
                        self.logger.info("Using existing Grafana API key")
                        return
            
            # Create new API key
            key_data = {
                "name": "algo_trader_api_key",
                "role": "Admin"
            }
            
            response = requests.post(
                f"{self.host}/api/auth/keys",
                json=key_data,
                auth=(self.admin_user, self.admin_password),
                timeout=10
            )
            
            if response.status_code == 200:
                self.api_key = response.json()['key']
                self.logger.info("Created new Grafana API key")
            else:
                raise RuntimeError(f"Failed to create API key: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error authenticating with Grafana: {e}")
            raise RuntimeError("Failed to authenticate with Grafana")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.
        
        If api_key is None (anonymous auth), returns only Content-Type header.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def create_or_update_datasource(self, datasource_config: Dict[str, Any]) -> bool:
        """
        Create or update a datasource in Grafana.
        
        Arguments:
            datasource_config: Datasource configuration dictionary
            
        Returns:
            True if datasource created/updated successfully, False otherwise
        """
        try:
            datasource_name = datasource_config.get('name', 'unknown')
            
            # Try to create first
            response = requests.post(
                f"{self.host}/api/datasources",
                json=datasource_config,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Created datasource: {datasource_name}")
                return True
            elif response.status_code == 409:
                # Datasource exists, try to update it
                # Get existing datasource to find its ID
                get_response = requests.get(
                    f"{self.host}/api/datasources/name/{datasource_name}",
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if get_response.status_code == 200:
                    existing_ds = get_response.json()
                    ds_id = existing_ds.get('id')
                    
                    # Update with the new config
                    datasource_config['id'] = ds_id
                    update_response = requests.put(
                        f"{self.host}/api/datasources/{ds_id}",
                        json=datasource_config,
                        headers=self._get_headers(),
                        timeout=10
                    )
                    
                    if update_response.status_code == 200:
                        self.logger.info(f"Updated datasource: {datasource_name}")
                        return True
                    else:
                        self.logger.error(f"Failed to update datasource: {update_response.status_code} - {update_response.text}")
                        return False
                else:
                    self.logger.error(f"Datasource exists but couldn't retrieve it: {get_response.status_code}")
                    return False
            else:
                self.logger.error(f"Failed to create datasource: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating/updating datasource: {e}")
            return False
    
    def create_or_update_dashboard(self, dashboard_config: Dict[str, Any]) -> bool:
        """
        Create or update a dashboard in Grafana.
        
        The dashboard_config should have "overwrite": true to update existing dashboards.
        
        Arguments:
            dashboard_config: Dashboard configuration dictionary
            
        Returns:
            True if dashboard created/updated successfully, False otherwise
        """
        try:
            dashboard_title = dashboard_config.get('dashboard', {}).get('title', 'unknown')
            
            # Ensure overwrite is set to true to handle existing dashboards
            dashboard_config['overwrite'] = True
            
            response = requests.post(
                f"{self.host}/api/dashboards/db",
                json=dashboard_config,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    if 'id' in result:
                        self.logger.info(f"Updated dashboard: {dashboard_title}")
                    else:
                        self.logger.info(f"Created dashboard: {dashboard_title}")
                    return True
                else:
                    self.logger.info(f"Created/Updated dashboard: {dashboard_title}")
                    return True
            else:
                self.logger.error(f"Failed to create/update dashboard: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating/updating dashboard: {e}")
            return False
    
    def get_dashboard(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get dashboard by UID.
        
        Arguments:
            uid: Dashboard UID
            
        Returns:
            Dashboard configuration if found, None otherwise
        """
        try:
            response = requests.get(
                f"{self.host}/api/dashboards/uid/{uid}",
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Dashboard not found: {uid}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting dashboard: {e}")
            return None
    
    def provision_datasources(self) -> bool:
        """
        Provision all datasources defined by the inheriting class.
        
        Returns:
            True if all datasources provisioned successfully, False otherwise
        """
        datasources = self.get_datasources()
        success_count = 0
        
        for datasource in datasources:
            if self.create_or_update_datasource(datasource):
                success_count += 1
        
        self.logger.info(f"Provisioned {success_count}/{len(datasources)} datasources")
        return success_count == len(datasources)
    
    def provision_dashboards(self) -> bool:
        """
        Provision all dashboards defined by the inheriting class.
        
        Returns:
            True if all dashboards provisioned successfully, False otherwise
        """
        dashboards = self.get_dashboards()
        success_count = 0
        
        for dashboard in dashboards:
            if self.create_or_update_dashboard(dashboard):
                success_count += 1
        
        self.logger.info(f"Provisioned {success_count}/{len(dashboards)} dashboards")
        return success_count == len(dashboards)
    
    def stop_container(self) -> bool:
        """
        Stop Grafana container.
        
        Returns:
            True if container stopped successfully, False otherwise
        """
        try:
            subprocess.run(
                ["docker", "stop", self.container_name],
                check=True,
                timeout=10
            )
            self.logger.info(f"Stopped Grafana container: {self.container_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping Grafana container: {e}")
            return False
    
    def remove_container(self) -> bool:
        """
        Remove Grafana container.
        
        Returns:
            True if container removed successfully, False otherwise
        """
        try:
            # Stop first if running
            self.stop_container()
            
            subprocess.run(
                ["docker", "rm", self.container_name],
                check=True,
                timeout=10
            )
            self.logger.info(f"Removed Grafana container: {self.container_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing Grafana container: {e}")
            return False
    
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
        Start Grafana container using docker-compose.
        
        Uses the project's docker-compose.yml for configuration.
        Waits for Grafana to be ready before returning.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            project_root = self.find_project_root()
            compose_file = project_root / "docker-compose.yml"
            compose_cmd = self.get_compose_command()
            
            if self._is_container_running():
                self.logger.info("Grafana is already running")
                return True
            
            self.logger.info("Starting Grafana container via docker-compose...")
            subprocess.run(
                [*compose_cmd, "-f", str(compose_file), "up", "-d", "grafana"],
                cwd=project_root,
                check=True,
                timeout=60
            )
            
            # Wait for Grafana to be ready
            self.logger.info("Waiting for Grafana to be ready...")
            for attempt in range(30):
                try:
                    response = requests.get(f"{self.host}/api/health", timeout=2)
                    if response.status_code == 200:
                        self.logger.info("✓ Grafana is ready!")
                        return True
                except Exception:
                    pass
                time.sleep(2)
            
            self.logger.warning("Grafana may not be fully ready yet")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Grafana: {e}")
            return False
    
    def stop_via_compose(self) -> bool:
        """
        Stop Grafana container using docker-compose.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            project_root = self.find_project_root()
            compose_file = project_root / "docker-compose.yml"
            compose_cmd = self.get_compose_command()
            
            if not self._is_container_running():
                self.logger.info("Grafana is not running")
                return True
            
            self.logger.info("Stopping Grafana container...")
            subprocess.run(
                [*compose_cmd, "-f", str(compose_file), "stop", "grafana"],
                cwd=project_root,
                check=True,
                timeout=30
            )
            self.logger.info("✓ Grafana stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop Grafana: {e}")
            return False
    
    def restart_via_compose(self) -> bool:
        """
        Restart Grafana container using docker-compose.
        
        Returns:
            True if restarted successfully, False otherwise
        """
        self.logger.info("Restarting Grafana...")
        if not self.stop_via_compose():
            return False
        time.sleep(2)
        return self.start_via_compose()
    
    def status_via_compose(self):
        """Show Grafana container status using docker-compose."""
        try:
            project_root = self.find_project_root()
            compose_file = project_root / "docker-compose.yml"
            compose_cmd = self.get_compose_command()
            
            subprocess.run(
                [*compose_cmd, "-f", str(compose_file), "ps", "grafana"],
                cwd=project_root
            )
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
    
    def logs_via_compose(self, follow: bool = True):
        """
        Show Grafana logs using docker-compose.
        
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
            cmd.append("grafana")
            
            subprocess.run(cmd, cwd=project_root)
        except Exception as e:
            self.logger.error(f"Failed to show logs: {e}")
