import os
import requests
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from influxdb_client_3 import InfluxDBError, Point

from infrastructure.clients.influx_client import (
    BatchWriteConfig, 
    BatchingCallback, 
    BaseInfluxDBClient
)


@pytest.mark.unit
class TestBatchWriteConfig:
    """Unit tests for BatchWriteConfig dataclass"""

    def test_default_initialization(self):
        """Test BatchWriteConfig initializes with default values"""
        config = BatchWriteConfig()
        assert config.batch_size == 100
        assert config.flush_interval == 10_000
        assert config.jitter_interval == 2_000
        assert config.retry_interval == 5_000
        assert config.max_retries == 5
        assert config.max_retry_delay == 30_000
        assert config.exponential_base == 2

    def test_custom_initialization(self):
        """Test BatchWriteConfig with custom values"""
        config = BatchWriteConfig(
            batch_size=50,
            max_retries=3,
            flush_interval=5_000
        )
        assert config.batch_size == 50
        assert config.max_retries == 3
        assert config.flush_interval == 5_000

    def test_validation_positive_batch_size(self):
        """Test validation fails for non-positive batch_size"""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BatchWriteConfig(batch_size=0)
        
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BatchWriteConfig(batch_size=-1)

    def test_validation_negative_max_retries(self):
        """Test validation fails for negative max_retries"""
        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            BatchWriteConfig(max_retries=-1)

    def test_validation_zero_max_retries_allowed(self):
        """Test zero max_retries is allowed"""
        config = BatchWriteConfig(max_retries=0)
        assert config.max_retries == 0

    @patch('infrastructure.clients.influx_client.WriteOptions')
    def test_to_write_options_conversion(self, mock_write_options):
        """Test conversion to WriteOptions format"""
        config = BatchWriteConfig(batch_size=200, max_retries=10)
        
        config._to_write_options()
        
        mock_write_options.assert_called_once_with(
            batch_size=200,
            flush_interval=10_000,
            jitter_interval=2_000,
            retry_interval=5_000,
            max_retries=10,
            max_retry_delay=30_000,
            exponential_base=2
        )


@pytest.mark.unit
class TestBatchingCallback:
    """Unit tests for BatchingCallback class"""

    def test_success_callback(self, capsys):
        """Test success callback prints expected message"""
        callback = BatchingCallback()
        test_conf = {"test": "config"}
        test_data = "sample data"
        
        callback.success(test_conf, test_data)
        
        captured = capsys.readouterr()
        assert "Written batch:" in captured.out
        assert str(test_conf) in captured.out

    def test_error_callback(self, capsys):
        """Test error callback prints expected message"""
        callback = BatchingCallback()
        test_conf = {"test": "config"}
        test_data = "sample data"
        test_exception = InfluxDBError(message="Test error")
        
        callback.error(test_conf, test_data, test_exception)
        
        captured = capsys.readouterr()
        assert "Cannot write batch:" in captured.out
        assert str(test_conf) in captured.out
        assert "sample data" in captured.out

    def test_retry_callback(self, capsys):
        """Test retry callback prints expected message"""
        callback = BatchingCallback()
        test_conf = {"test": "config"}
        test_data = "sample data"
        test_exception = InfluxDBError(message="Retry error")
        
        callback.retry(test_conf, test_data, test_exception)
        
        captured = capsys.readouterr()
        assert "Retryable error occurs for batch:" in captured.out
        assert str(test_conf) in captured.out
        assert "sample data" in captured.out


@pytest.mark.unit
class TestBaseInfluxDBClient:
    """Unit tests for BaseInfluxDBClient class"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock environment variables"""
        with patch.dict(os.environ, {
            'INFLUXDB3_AUTH_TOKEN': 'test_token',
            'INFLUXDB3_HTTP_BIND_ADDR': 'test-url:test-port'  # No http:// prefix - let the class add it
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('infrastructure.clients.influx_client.get_logger') as mock_logger, \
             patch('infrastructure.clients.influx_client.InfluxDBClient3') as mock_client_class, \
             patch('infrastructure.clients.influx_client.write_client_options') as mock_wco, \
             patch('infrastructure.clients.influx_client.BaseInfluxDBClient.ping') as mock_ping, \
             patch('infrastructure.clients.influx_client.BaseInfluxDBClient._start_server') as mock_start_server:
            
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_ping.return_value = True
            mock_start_server.return_value = True
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'client_class': mock_client_class,
                'client': mock_client,
                'wco': mock_wco,
                'ping': mock_ping,
                'start_server': mock_start_server
            }

    def test_initialization(self, mock_dependencies):
        """Test BaseInfluxDBClient initialization"""
        database = "test_db"
        
        client = BaseInfluxDBClient(database)
        
        assert client.database == database
        assert client.url == "http://test-url:test-port"
        assert client.token == "test_token"
        
        mock_dependencies['client_class'].assert_called_once_with(
            token="test_token",
            host="http://test-url:test-port",
            database=database
        )

    def test_write_point_success(self, mock_dependencies):
        """Test successful write_point operation"""
        client = BaseInfluxDBClient("test_db")
        mock_client = mock_dependencies['client']
        
        result = client.write_point("measurement", "test_data", "test_name", {"env": "prod", "service": "api"})
        
        mock_client.write.assert_called_once()
        mock_dependencies['logger_instance'].info.assert_called_with(
            "Writing data point to test_name"
        )

    def test_write_point_failure(self, mock_dependencies):
        """Test write_point with exception handling"""
        client = BaseInfluxDBClient("test_db")
        mock_client = mock_dependencies['client']
        mock_client.write.side_effect = Exception("Write failed")
        
        client.write_point("measurement", "test_data", "test_name", {"env": "test", "host": "server1"})
        
        mock_dependencies['logger_instance'].error.assert_called_with(
            "Failed to write point to database: Write failed"
        )

    def test_write_batch_success(self, mock_dependencies):
        """Test successful write_batch operation"""
        client = BaseInfluxDBClient("test_db")
        mock_client = mock_dependencies['client']
        test_df = pd.DataFrame({"col1": [1, 2, 3]})
        
        result = client.write_batch(test_df, "test_measurement", ["tag1"])
        
        assert result is True
        mock_client.write.assert_called_once_with(
            test_df, 
            data_frame_measurement_name="test_measurement",
            data_frame_gat_colums=["tag1"]
        )

    def test_write_batch_failure(self, mock_dependencies):
        """Test write_batch with exception handling"""
        client = BaseInfluxDBClient("test_db")
        mock_client = mock_dependencies['client']
        mock_client.write.side_effect = Exception("Batch write failed")
        test_df = pd.DataFrame({"col1": [1, 2, 3]})
        
        result = client.write_batch(test_df, "test_measurement", ["tag1"])
        
        assert result is False
        mock_dependencies['logger_instance'].error.assert_called_with(
            "Error writing batch to database: Batch write failed"
        )

    def test_query_data_success(self, mock_dependencies):
        """Test successful query_data operation"""
        client = BaseInfluxDBClient("test_db")
        mock_client = mock_dependencies['client']
        expected_df = pd.DataFrame({"result": [1, 2, 3]})
        mock_client.query.return_value = expected_df
        
        result = client.query_data("SELECT * FROM test", "sql", "pandas")
        
        pd.testing.assert_frame_equal(result, expected_df)
        mock_client.query.assert_called_once_with("SELECT * FROM test", "sql", "pandas")

    def test_query_data_failure(self, mock_dependencies):
        """Test query_data with exception handling"""
        client = BaseInfluxDBClient("test_db")
        mock_client = mock_dependencies['client']
        mock_client.query.side_effect = Exception("Query failed")
        
        result = client.query_data("SELECT * FROM test")
        
        assert result is None
        mock_dependencies['logger_instance'].error.assert_called_with(
            "Failed to query database: Query failed"
        )

    def test_get_write_config_returns_default(self, mock_dependencies):
        """Test _get_write_config returns default BatchWriteConfig"""
        client = BaseInfluxDBClient("test_db")
        config = client._get_write_config()
        
        assert isinstance(config, BatchWriteConfig)
        assert config.batch_size == 100

    def test_ping_success(self, mock_env_vars):
        """Test successful ping to InfluxDB server"""
        with patch('infrastructure.clients.influx_client.get_logger'), \
             patch('infrastructure.clients.influx_client.InfluxDBClient3'), \
             patch('infrastructure.clients.influx_client.write_client_options'), \
             patch('infrastructure.clients.influx_client.BaseInfluxDBClient._start_server'), \
             patch('infrastructure.clients.influx_client.requests.get') as mock_get:
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            client = BaseInfluxDBClient("test_db")
            result = client.ping()
            
            assert result is True
            mock_get.assert_called_once_with(
                "http://test-url:test-port/health",
                headers={"Authorization": "Bearer test_token"}
            )

    def test_ping_failure(self, mock_env_vars):
        """Test ping failure when server is not responding"""
        with patch('infrastructure.clients.influx_client.get_logger'), \
             patch('infrastructure.clients.influx_client.InfluxDBClient3'), \
             patch('infrastructure.clients.influx_client.write_client_options'), \
             patch('infrastructure.clients.influx_client.BaseInfluxDBClient._start_server'), \
             patch('infrastructure.clients.influx_client.requests.get') as mock_get:
            
            mock_get.side_effect = Exception("Connection failed")
            
            client = BaseInfluxDBClient("test_db")
            result = client.ping()
            
            assert result is False


@pytest.mark.integration
class TestInfluxDBClientIntegration:
    """Integration tests for InfluxDB client (requires local InfluxDB running)"""

    @pytest.fixture(scope="session")
    def influx_client(self):
        """Create client connected to local InfluxDB"""        
        client = BaseInfluxDBClient(database="test")
        return client

    def test_write_point_method(self, influx_client):
        """Test writing data using the write_point wrapper method"""
        # Write test data using your wrapper method
        influx_client.write_point(
            measurement="home",
            data=25.3,
            name="temp",
            tags={"room": "Kitchen", "sensor": "thermometer"}
        )
        
        influx_client.write_point(
            measurement="home", 
            data=20.2,
            name="humidity",
            tags={"room": "Kitchen", "sensor": "hygrometer"}
        )
        
        # Verify data was written by querying back using your wrapper method
        query = "SELECT * FROM home ORDER BY time DESC LIMIT 10"
        result = influx_client.query_data(query)
        
        assert result is not None, "Query should return data"
        assert len(result) >= 2, "Should have at least 2 records"
        print(f"Successfully wrote and retrieved {len(result)} records")
