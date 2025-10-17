"""Unit and integration tests for SECDataSource."""
import pytest
from unittest.mock import MagicMock, patch
from system.algo_trader.datasources.sec import SECDataSource
from system.algo_trader.clients.influxdb_client import AlgoTraderInfluxDBClient


@pytest.mark.unit
class TestSECDataSourceUnit:
    """Unit tests for SECDataSource with mocking."""
    
    def test_init_without_client(self):
        """Test SECDataSource initialization without InfluxDB client."""
        source = SECDataSource()
        
        assert source.influxdb_client is None
        assert source._ticker_cache is None
        assert source.logger is not None
    
    def test_init_with_client(self):
        """Test SECDataSource initialization with InfluxDB client."""
        mock_client = MagicMock()
        source = SECDataSource(influxdb_client=mock_client)
        
        assert source.influxdb_client == mock_client
        assert source._ticker_cache is None
    
    @patch('requests.get')
    def test_fetch_tickers_success(self, mock_get):
        """Test successful ticker fetch from SEC API."""
        # Mock SEC API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
            "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."}
        }
        mock_get.return_value = mock_response
        
        source = SECDataSource(user_agent="TestSuite test@example.com")
        tickers = source.fetch_tickers()
        
        assert tickers is not None
        assert len(tickers) == 3
        assert tickers[0]['ticker'] == 'AAPL'
        assert tickers[0]['cik_str'] == '320193'
        assert tickers[0]['title'] == 'Apple Inc.'
        assert tickers[1]['ticker'] == 'MSFT'
        assert tickers[2]['ticker'] == 'GOOGL'
        
        # Verify User-Agent header was set
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert 'headers' in call_args[1]
        assert call_args[1]['headers']['User-Agent'] == "TestSuite test@example.com"
    
    @patch('requests.get')
    def test_fetch_tickers_network_error(self, mock_get):
        """Test ticker fetch with network error."""
        mock_get.side_effect = Exception("Network error")
        
        source = SECDataSource()
        tickers = source.fetch_tickers()
        
        assert tickers is None
        assert source._ticker_cache is None
    
    @patch('requests.get')
    def test_fetch_tickers_http_error(self, mock_get):
        """Test ticker fetch with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_response
        
        source = SECDataSource()
        tickers = source.fetch_tickers()
        
        assert tickers is None
    
    @patch('requests.get')
    def test_get_ticker_symbols(self, mock_get):
        """Test getting ticker symbols only."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"}
        }
        mock_get.return_value = mock_response
        
        source = SECDataSource()
        symbols = source.get_ticker_symbols()
        
        assert symbols is not None
        assert len(symbols) == 2
        assert symbols == ['AAPL', 'MSFT']
    
    @patch('requests.get')
    def test_get_ticker_symbols_cached(self, mock_get):
        """Test getting ticker symbols from cache without refetching."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_get.return_value = mock_response
        
        source = SECDataSource()
        
        # First call should fetch
        symbols1 = source.get_ticker_symbols()
        assert mock_get.call_count == 1
        
        # Second call should use cache
        symbols2 = source.get_ticker_symbols()
        assert mock_get.call_count == 1  # No additional call
        assert symbols1 == symbols2
    
    def test_store_tickers_no_client(self):
        """Test storing tickers without InfluxDB client."""
        source = SECDataSource()
        
        tickers = [
            {"ticker": "AAPL", "cik_str": "320193", "title": "Apple Inc."}
        ]
        
        result = source.store_tickers_in_influxdb(tickers)
        
        assert result is False
    
    @patch('requests.get')
    def test_store_tickers_success(self, mock_get):
        """Test successful ticker storage in InfluxDB."""
        # Mock fetch
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"}
        }
        mock_get.return_value = mock_response
        
        # Mock InfluxDB client
        mock_client = MagicMock()
        mock_client.write_points.return_value = True
        
        source = SECDataSource(influxdb_client=mock_client)
        source.fetch_tickers()
        
        result = source.store_tickers_in_influxdb()
        
        assert result is True
        mock_client.write_points.assert_called_once()
        
        # Verify points structure
        call_args = mock_client.write_points.call_args
        points = call_args[0][0]
        assert len(points) == 2
    
    def test_store_tickers_with_provided_data(self):
        """Test storing tickers with provided data (no fetch needed)."""
        mock_client = MagicMock()
        mock_client.write_points.return_value = True
        
        source = SECDataSource(influxdb_client=mock_client)
        
        tickers = [
            {"ticker": "AAPL", "cik_str": "320193", "title": "Apple Inc."}
        ]
        
        result = source.store_tickers_in_influxdb(tickers)
        
        assert result is True
        mock_client.write_points.assert_called_once()
    
    def test_store_tickers_empty_list(self):
        """Test storing empty ticker list."""
        mock_client = MagicMock()
        source = SECDataSource(influxdb_client=mock_client)
        
        result = source.store_tickers_in_influxdb(tickers=[])
        
        assert result is False
        mock_client.write_points.assert_not_called()
    
    @patch('requests.get')
    def test_store_tickers_write_failure(self, mock_get):
        """Test ticker storage with InfluxDB write failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_get.return_value = mock_response
        
        mock_client = MagicMock()
        mock_client.write_points.return_value = False
        
        source = SECDataSource(influxdb_client=mock_client)
        source.fetch_tickers()
        
        result = source.store_tickers_in_influxdb()
        
        assert result is False
    
    @patch('requests.get')
    def test_get_ticker_count(self, mock_get):
        """Test getting ticker count."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
            "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."}
        }
        mock_get.return_value = mock_response
        
        source = SECDataSource()
        
        # Before fetch
        assert source.get_ticker_count() == 0
        
        # After fetch
        source.fetch_tickers()
        assert source.get_ticker_count() == 3


@pytest.mark.integration
class TestSECDataSourceIntegration:
    """Integration tests for SECDataSource with real external services."""
    
    def test_fetch_tickers_from_sec(self):
        """Test fetching real ticker data from SEC API."""
        # Use proper User-Agent for SEC compliance
        source = SECDataSource(user_agent="AlgoTraderTest test@example.com")
        tickers = source.fetch_tickers()
        
        # Verify we got data
        assert tickers is not None
        assert len(tickers) > 0
        
        # Verify structure of first ticker
        first_ticker = tickers[0]
        assert 'ticker' in first_ticker
        assert 'cik_str' in first_ticker
        assert 'title' in first_ticker
        assert isinstance(first_ticker['ticker'], str)
        assert isinstance(first_ticker['cik_str'], str)
        assert isinstance(first_ticker['title'], str)
        
        # Verify some well-known tickers exist
        ticker_symbols = [t['ticker'] for t in tickers]
        assert 'AAPL' in ticker_symbols or 'MSFT' in ticker_symbols
    
    def test_get_ticker_symbols_from_sec(self):
        """Test getting ticker symbol list from SEC."""
        source = SECDataSource(user_agent="AlgoTraderTest test@example.com")
        symbols = source.get_ticker_symbols()
        
        assert symbols is not None
        assert len(symbols) > 100  # Should have many tickers
        assert all(isinstance(s, str) for s in symbols)
    
    def test_store_tickers_in_influxdb_real(self):
        """Test storing ticker data in real InfluxDB instance."""
        # Initialize real clients
        influx_client = AlgoTraderInfluxDBClient()
        source = SECDataSource(
            influxdb_client=influx_client,
            user_agent="AlgoTraderTest test@example.com"
        )
        
        try:
            # Fetch and store tickers
            tickers = source.fetch_tickers()
            assert tickers is not None
            
            result = source.store_tickers_in_influxdb(tickers)
            assert result is True
            
            # Query to verify tickers were stored
            sql = "SELECT * FROM ticker_metadata LIMIT 10"
            query_result = influx_client.query(sql)
            
            assert query_result is not None
            assert len(query_result) > 0
            # Pandas DataFrame has columns attribute
            assert 'ticker' in query_result.columns
            assert 'cik' in query_result.columns
            assert 'title' in query_result.columns
            
        finally:
            influx_client.close()
    
    def test_ticker_filtering_with_market_data(self):
        """Test that stored tickers can be used to filter market data."""
        influx_client = AlgoTraderInfluxDBClient()
        source = SECDataSource(
            influxdb_client=influx_client,
            user_agent="AlgoTraderTest test@example.com"
        )
        
        try:
            # Fetch and store tickers
            tickers = source.fetch_tickers()
            assert tickers is not None
            
            source.store_tickers_in_influxdb(tickers)
            
            # Query ticker metadata for a specific ticker
            sql = "SELECT * FROM ticker_metadata WHERE ticker = 'AAPL' LIMIT 1"
            result = influx_client.query(sql)
            
            if result is not None and len(result) > 0:
                # Verify we can query using the ticker tag (pandas DataFrame)
                assert result.iloc[0]['ticker'] == 'AAPL'
                assert 'cik' in result.columns
                assert 'title' in result.columns
                
        finally:
            influx_client.close()

