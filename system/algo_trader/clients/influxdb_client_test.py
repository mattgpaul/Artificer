"""
Unit and integration tests for AlgoTraderInfluxDBClient.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from system.algo_trader.clients.influxdb_client import AlgoTraderInfluxDBClient


@pytest.mark.unit
class TestAlgoTraderInfluxDBClientUnit:
    """Unit tests for AlgoTraderInfluxDBClient."""
    
    @patch('infrastructure.clients.influxdb_client.InfluxDBClient3')
    @patch('os.getenv')
    def test_initialization(self, mock_getenv, mock_influx_client):
        """Test client initialization with mocked environment."""
        mock_getenv.side_effect = lambda key, default="": {
            'ALGO_TRADER_INFLUXDB_HOST': 'test-host:8181',
            'ALGO_TRADER_INFLUXDB_DATABASE': 'test-database',
            'INFLUXDB3_AUTH_TOKEN': 'test_token',
            'INFLUXDB3_CONTAINER_NAME': 'test-container',
            'INFLUXDB3_PORT': '8181'
        }.get(key, default)
        
        # auto_start=False prevents container startup during init
        client = AlgoTraderInfluxDBClient(auto_start=False)
        
        assert client.database == "test-database"
        assert client.host == "test-host:8181"
        assert client.token == "test_token"
        assert client.container_name == "test-container"
        mock_influx_client.assert_called_once()
    
    @patch('infrastructure.clients.influxdb_client.InfluxDBClient3')
    @patch('os.getenv')
    def test_write_candle_data_success(self, mock_getenv, mock_influx_client):
        """Test writing candle data successfully."""
        mock_getenv.side_effect = lambda key, default="": {
            'ALGO_TRADER_INFLUXDB_HOST': 'localhost:8181',
            'INFLUXDB3_PORT': '8181',
            'ALGO_TRADER_INFLUXDB_DATABASE': 'test-db',
            'INFLUXDB3_AUTH_TOKEN': '',
            'INFLUXDB3_CONTAINER_NAME': 'test-container'
        }.get(key, default)
        mock_client_instance = MagicMock()
        mock_influx_client.return_value = mock_client_instance
        
        client = AlgoTraderInfluxDBClient(auto_start=False)
        
        candles = [
            {
                'datetime': 1609459200000,  # 2021-01-01 00:00:00
                'open': 100.0,
                'high': 105.0,
                'low': 99.0,
                'close': 103.0,
                'volume': 1000000
            },
            {
                'datetime': 1609545600000,  # 2021-01-02 00:00:00
                'open': 103.0,
                'high': 108.0,
                'low': 102.0,
                'close': 107.0,
                'volume': 1500000
            }
        ]
        
        result = client.write_candle_data(
            ticker="AAPL",
            period_type="month",
            period=1,
            frequency_type="daily",
            frequency=1,
            candles=candles
        )
        
        assert result is True
        assert mock_client_instance.write.called
    
    @patch('infrastructure.clients.influxdb_client.InfluxDBClient3')
    @patch('os.getenv')
    def test_write_candle_data_empty(self, mock_getenv, mock_influx_client):
        """Test writing empty candle data."""
        mock_getenv.side_effect = lambda key, default="": {
            'ALGO_TRADER_INFLUXDB_HOST': 'localhost:8181',
            'INFLUXDB3_PORT': '8181',
            'ALGO_TRADER_INFLUXDB_DATABASE': 'test-db',
            'INFLUXDB3_AUTH_TOKEN': '',
            'INFLUXDB3_CONTAINER_NAME': 'test-container'
        }.get(key, default)
        
        client = AlgoTraderInfluxDBClient(auto_start=False)
        
        result = client.write_candle_data(
            ticker="AAPL",
            period_type="month",
            period=1,
            frequency_type="daily",
            frequency=1,
            candles=[]
        )
        
        assert result is False
    
    @patch('infrastructure.clients.influxdb_client.InfluxDBClient3')
    @patch('os.getenv')
    def test_write_candle_data_missing_timestamp(self, mock_getenv, mock_influx_client):
        """Test writing candle data with missing timestamp."""
        mock_getenv.side_effect = lambda key, default="": {
            'ALGO_TRADER_INFLUXDB_HOST': 'localhost:8181',
            'INFLUXDB3_PORT': '8181',
            'ALGO_TRADER_INFLUXDB_DATABASE': 'test-db',
            'INFLUXDB3_AUTH_TOKEN': '',
            'INFLUXDB3_CONTAINER_NAME': 'test-container'
        }.get(key, default)
        mock_client_instance = MagicMock()
        mock_influx_client.return_value = mock_client_instance
        
        client = AlgoTraderInfluxDBClient(auto_start=False)
        
        candles = [
            {
                'open': 100.0,
                'high': 105.0,
                'low': 99.0,
                'close': 103.0,
                'volume': 1000000
                # Missing 'datetime' field
            }
        ]
        
        result = client.write_candle_data(
            ticker="AAPL",
            period_type="month",
            period=1,
            frequency_type="daily",
            frequency=1,
            candles=candles
        )
        
        assert result is False
    
    @patch('infrastructure.clients.influxdb_client.InfluxDBClient3')
    @patch('os.getenv')
    def test_query_candles_with_filters(self, mock_getenv, mock_influx_client):
        """Test querying candles with various filters."""
        mock_getenv.side_effect = lambda key, default="": {
            'ALGO_TRADER_INFLUXDB_HOST': 'localhost:8181',
            'INFLUXDB3_PORT': '8181',
            'ALGO_TRADER_INFLUXDB_DATABASE': 'test-db',
            'INFLUXDB3_AUTH_TOKEN': '',
            'INFLUXDB3_CONTAINER_NAME': 'test-container'
        }.get(key, default)
        mock_client_instance = MagicMock()
        mock_influx_client.return_value = mock_client_instance
        
        # Mock query result
        mock_result = MagicMock()
        mock_client_instance.query.return_value = mock_result
        
        client = AlgoTraderInfluxDBClient(auto_start=False)
        
        result = client.query_candles(
            ticker="AAPL",
            period_type="month",
            period=1,
            frequency_type="daily",
            frequency=1
        )
        
        assert result is not None
        assert mock_client_instance.query.called
    
    @patch('infrastructure.clients.influxdb_client.InfluxDBClient3')
    @patch('os.getenv')
    def test_get_available_tickers_success(self, mock_getenv, mock_influx_client):
        """Test getting available tickers."""
        mock_getenv.side_effect = lambda key, default="": {
            'ALGO_TRADER_INFLUXDB_HOST': 'localhost:8181',
            'INFLUXDB3_PORT': '8181',
            'ALGO_TRADER_INFLUXDB_DATABASE': 'test-db',
            'INFLUXDB3_AUTH_TOKEN': '',
            'INFLUXDB3_CONTAINER_NAME': 'test-container'
        }.get(key, default)
        mock_client_instance = MagicMock()
        mock_influx_client.return_value = mock_client_instance
        
        # Mock query result with ticker data
        mock_result = MagicMock()
        mock_result.empty = False
        mock_result.__getitem__.return_value.unique.return_value.tolist.return_value = ['AAPL', 'MSFT', 'GOOGL']
        mock_client_instance.query.return_value = mock_result
        
        client = AlgoTraderInfluxDBClient(auto_start=False)
        tickers = client.get_available_tickers()
        
        assert tickers is not None
        assert len(tickers) == 3
        assert 'AAPL' in tickers
    
    @patch('infrastructure.clients.influxdb_client.InfluxDBClient3')
    @patch('os.getenv')
    def test_close_connection(self, mock_getenv, mock_influx_client):
        """Test closing InfluxDB connection."""
        mock_getenv.side_effect = lambda key, default="": {
            'ALGO_TRADER_INFLUXDB_HOST': 'localhost:8181',
            'INFLUXDB3_PORT': '8181',
            'ALGO_TRADER_INFLUXDB_DATABASE': 'test-db',
            'INFLUXDB3_AUTH_TOKEN': '',
            'INFLUXDB3_CONTAINER_NAME': 'test-container'
        }.get(key, default)
        mock_client_instance = MagicMock()
        mock_influx_client.return_value = mock_client_instance
        
        client = AlgoTraderInfluxDBClient(auto_start=False)
        client.close()
        
        assert mock_client_instance.close.called


@pytest.mark.integration
class TestAlgoTraderInfluxDBClientIntegration:
    """Integration tests for AlgoTraderInfluxDBClient."""
    
    def test_write_and_query_real_data(self):
        """Test writing and querying real data from InfluxDB."""
        # This test requires a running InfluxDB Docker container
        # Start container with: bazel run //infrastructure/clients:influxdb start
        client = AlgoTraderInfluxDBClient(auto_start=False)
        
        # Write test data
        candles = [
            {
                'datetime': int(datetime.now().timestamp() * 1000),
                'open': 100.0,
                'high': 105.0,
                'low': 99.0,
                'close': 103.0,
                'volume': 1000000
            }
        ]
        
        write_result = client.write_candle_data(
            ticker="TEST_TICKER",
            period_type="day",
            period=1,
            frequency_type="daily",
            frequency=1,
            candles=candles
        )
        
        assert write_result is True
        
        # Query the data back
        query_result = client.query_candles(ticker="TEST_TICKER")
        assert query_result is not None
        
        # Cleanup
        client.close()

