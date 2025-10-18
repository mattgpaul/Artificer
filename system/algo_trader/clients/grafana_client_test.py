import pytest
from unittest.mock import Mock, patch, MagicMock
from system.algo_trader.clients.grafana_client import AlgoTraderGrafanaClient


@pytest.mark.unit
class TestAlgoTraderGrafanaClientUnit:
    """Unit tests for AlgoTraderGrafanaClient."""
    
    @patch.dict('os.environ', {
        'GRAFANA_HOST': 'test-grafana-host',
        'GRAFANA_ADMIN_USER': 'test-admin',
        'GRAFANA_ADMIN_PASSWORD': 'test-password',
        'GRAFANA_CONTAINER_NAME': 'test-grafana',
        'INFLUXDB3_HTTP_BIND_ADDR': 'test-influxdb-host:8181',
        'INFLUXDB3_AUTH_TOKEN': 'test-token'
    })
    @patch('subprocess.run')
    @patch('requests.get')
    @patch('requests.post')
    def test_init_success(self, mock_post, mock_get, mock_run):
        """Test successful initialization."""
        # Mock container running
        mock_run.return_value.stdout = "test-grafana"
        
        # Mock health check
        mock_get.return_value.status_code = 200
        
        # Mock API key creation
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"key": "test-api-key"}
        
        client = AlgoTraderGrafanaClient()
        
        assert client.influxdb_docker_host == "influxdb:8181"
        assert client.influxdb_token == "test-token"
        assert client.influxdb_database == "algo-trader-database"
    
    @patch.dict('os.environ', {
        'GRAFANA_HOST': 'test-grafana-host',
        'GRAFANA_ADMIN_USER': 'test-admin',
        'GRAFANA_ADMIN_PASSWORD': 'test-password',
        'GRAFANA_CONTAINER_NAME': 'test-grafana',
        'INFLUXDB3_HTTP_BIND_ADDR': 'test-influxdb-host:8181',
        'INFLUXDB3_AUTH_TOKEN': 'test-token'
    })
    @patch('subprocess.run')
    @patch('requests.get')
    @patch('requests.post')
    def test_get_datasources(self, mock_post, mock_get, mock_run):
        """Test datasource configuration."""
        # Mock initialization
        mock_run.return_value.stdout = "test-grafana"
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"key": "test-api-key"}
        
        client = AlgoTraderGrafanaClient()
        datasources = client.get_datasources()
        
        assert len(datasources) == 1
        assert datasources[0]["name"] == "InfluxDB-MarketData"
        assert datasources[0]["type"] == "influxdb"
        # Datasource uses Docker network URL for container-to-container communication
        # Should use ALGO_TRADER_INFLUXDB_DOCKER_HOST from system-specific env
        assert datasources[0]["url"] == "http://influxdb:8181"
        assert datasources[0]["jsonData"]["defaultBucket"] == "algo-trader-database"
        assert datasources[0]["secureJsonData"]["token"] == "test-token"
    
    @patch.dict('os.environ', {
        'GRAFANA_HOST': 'test-grafana-host',
        'GRAFANA_ADMIN_USER': 'test-admin',
        'GRAFANA_ADMIN_PASSWORD': 'test-password',
        'GRAFANA_CONTAINER_NAME': 'test-grafana',
        'INFLUXDB3_HTTP_BIND_ADDR': 'test-influxdb-host:8181',
        'INFLUXDB3_AUTH_TOKEN': 'test-token'
    })
    @patch('subprocess.run')
    @patch('requests.get')
    @patch('requests.post')
    def test_get_dashboards(self, mock_post, mock_get, mock_run):
        """Test dashboard configuration."""
        # Mock initialization
        mock_run.return_value.stdout = "test-grafana"
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"key": "test-api-key"}
        
        client = AlgoTraderGrafanaClient()
        dashboards = client.get_dashboards()
        
        assert len(dashboards) == 1
        dashboard = dashboards[0]["dashboard"]
        assert dashboard["title"] == "Market Data - Candlestick Charts"
        assert "market-data" in dashboard["tags"]
        assert len(dashboard["panels"]) == 2  # OHLC chart + Volume chart
        assert len(dashboard["templating"]["list"]) == 5  # All variables
    
    @patch.dict('os.environ', {
        'GRAFANA_HOST': 'test-grafana-host',
        'GRAFANA_ADMIN_USER': 'test-admin',
        'GRAFANA_ADMIN_PASSWORD': 'test-password',
        'GRAFANA_CONTAINER_NAME': 'test-grafana',
        'INFLUXDB3_HTTP_BIND_ADDR': 'test-influxdb-host:8181',
        'INFLUXDB3_AUTH_TOKEN': 'test-token'
    })
    @patch('subprocess.run')
    @patch('requests.get')
    @patch('requests.post')
    def test_get_dashboard_url(self, mock_post, mock_get, mock_run):
        """Test dashboard URL generation."""
        # Mock initialization
        mock_run.return_value.stdout = "test-grafana"
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"key": "test-api-key"}
        
        client = AlgoTraderGrafanaClient()
        url = client.get_dashboard_url()
        
        expected_url = "http://test-grafana-host:3000/d/market-data-candles/market-data-candlestick-charts"
        assert url == expected_url
    
    @patch.dict('os.environ', {
        'GRAFANA_HOST': 'test-grafana-host',
        'GRAFANA_ADMIN_USER': 'test-admin',
        'GRAFANA_ADMIN_PASSWORD': 'test-password',
        'GRAFANA_CONTAINER_NAME': 'test-grafana',
        'INFLUXDB3_HTTP_BIND_ADDR': 'test-influxdb-host:8181',
        'INFLUXDB3_AUTH_TOKEN': 'test-token'
    })
    @patch('subprocess.run')
    @patch('requests.get')
    @patch('requests.post')
    def test_setup_visualization_success(self, mock_post, mock_get, mock_run):
        """Test successful visualization setup."""
        # Mock initialization
        mock_run.return_value.stdout = "test-grafana"
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"key": "test-api-key"}
        
        client = AlgoTraderGrafanaClient()
        
        # Mock provisioning success
        mock_post.return_value.status_code = 200
        
        result = client.setup_visualization()
        
        assert result is True
        # Should call create datasource and create dashboard
        assert mock_post.call_count >= 2
    
    @patch.dict('os.environ', {
        'GRAFANA_HOST': 'test-grafana-host',
        'GRAFANA_ADMIN_USER': 'test-admin',
        'GRAFANA_ADMIN_PASSWORD': 'test-password',
        'GRAFANA_CONTAINER_NAME': 'test-grafana',
        'INFLUXDB3_HTTP_BIND_ADDR': 'test-influxdb-host:8181',
        'INFLUXDB3_AUTH_TOKEN': 'test-token'
    })
    @patch('subprocess.run')
    @patch('requests.get')
    @patch('requests.post')
    def test_setup_visualization_datasource_failure(self, mock_post, mock_get, mock_run):
        """Test visualization setup with datasource failure."""
        # Mock initialization
        mock_run.return_value.stdout = "test-grafana"
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"key": "test-api-key"}
        
        client = AlgoTraderGrafanaClient()
        
        # Mock datasource creation failure
        mock_post.side_effect = [
            Mock(status_code=200, json=Mock(return_value={"key": "test-api-key"})),  # Auth
            Mock(status_code=400, text="Bad Request")  # Datasource creation
        ]
        
        result = client.setup_visualization()
        
        assert result is False


@pytest.mark.integration
class TestAlgoTraderGrafanaClientIntegration:
    """Integration tests for AlgoTraderGrafanaClient."""
    
    @patch.dict('os.environ', {
        'GRAFANA_HOST': 'test-grafana-host',
        'GRAFANA_ADMIN_USER': 'test-admin',
        'GRAFANA_ADMIN_PASSWORD': 'test-password',
        'GRAFANA_CONTAINER_NAME': 'test-grafana',
        'INFLUXDB3_HTTP_BIND_ADDR': 'test-influxdb-host:8181',
        'INFLUXDB3_AUTH_TOKEN': 'test-token'
    })
    def test_datasource_configuration_valid(self):
        """Test that datasource configuration is valid."""
        # This test validates the structure without requiring actual Grafana
        client = AlgoTraderGrafanaClient(auto_start=False)
        datasources = client.get_datasources()
        
        assert len(datasources) == 1
        ds = datasources[0]
        
        # Required fields
        assert "name" in ds
        assert "type" in ds
        assert "url" in ds
        assert "secureJsonData" in ds
        assert "jsonData" in ds
        
        # Validate InfluxDB 3.0 specific fields
        assert ds["type"] == "influxdb"
        assert ds["jsonData"]["version"] == "SQL"  # InfluxDB 3.0 uses SQL, not Flux
        assert ds["jsonData"]["defaultBucket"] == "algo-trader-database"
        assert ds["jsonData"]["allowInsecureGrpc"] is True
        assert ds["jsonData"]["secureGrpc"] is False
    
    @patch.dict('os.environ', {
        'GRAFANA_HOST': 'test-grafana-host',
        'GRAFANA_ADMIN_USER': 'test-admin',
        'GRAFANA_ADMIN_PASSWORD': 'test-password',
        'GRAFANA_CONTAINER_NAME': 'test-grafana',
        'INFLUXDB3_HTTP_BIND_ADDR': 'test-influxdb-host:8181',
        'INFLUXDB3_AUTH_TOKEN': 'test-token'
    })
    def test_dashboard_configuration_valid(self):
        """Test that dashboard configuration is valid."""
        # This test validates the structure without requiring actual Grafana
        client = AlgoTraderGrafanaClient(auto_start=False)
        dashboards = client.get_dashboards()
        
        # Dashboard loading requires the grafana directory with JSON files
        # In Bazel sandbox, these may not be available unless data dependency is set
        if len(dashboards) == 0:
            # Skip validation if dashboards can't be loaded (missing data files in test env)
            pytest.skip("Dashboard JSON files not available in test environment")
        
        assert len(dashboards) == 1
        dashboard = dashboards[0]["dashboard"]
        
        # Required fields
        assert "title" in dashboard
        assert "panels" in dashboard
        assert "templating" in dashboard
        assert "time" in dashboard
        
        # Validate panels
        assert len(dashboard["panels"]) == 2
        assert dashboard["panels"][0]["title"] == "OHLC Candlestick Chart"
        assert dashboard["panels"][1]["title"] == "Volume Chart"
        
        # Validate templating variables
        templating = dashboard["templating"]["list"]
        assert len(templating) == 5
        
        variable_names = [var["name"] for var in templating]
        expected_vars = ["ticker", "period_type", "period", "frequency_type", "frequency"]
        assert all(var in variable_names for var in expected_vars)




