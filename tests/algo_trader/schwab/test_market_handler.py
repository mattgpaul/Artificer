"""
Unit tests for MarketHandler - Market Data API Methods

Tests cover market data retrieval methods including quotes, price history,
and market hours. All external dependencies are mocked to avoid network calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class TestMarketHandlerInitialization:
    """Test MarketHandler initialization"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict('os.environ', {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.market_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.market_handler.SchwabClient') as mock_client_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'client_class': mock_client_class,
                'client': mock_client
            }

    def test_initialization_success(self, mock_dependencies):
        """Test successful MarketHandler initialization"""
        handler = MarketHandler()
        
        assert handler.market_url == "https://api.schwabapi.com/marketdata/v1"
        assert handler.logger is not None
        mock_dependencies['client_class'].assert_called_once()


class TestMarketHandlerRequestMethods:
    """Test request handling methods"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict('os.environ', {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.market_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.market_handler.SchwabClient') as mock_client_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'client_class': mock_client_class,
                'client': mock_client
            }

    def test_send_request_success(self, mock_dependencies):
        """Test successful request sending"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'test': 'data'}
        mock_dependencies['client'].make_authenticated_request.return_value = mock_response
        
        handler = MarketHandler()
        result = handler._send_request('https://api.test.com/test', {'param': 'value'})
        
        assert result == {'test': 'data'}
        mock_dependencies['client'].make_authenticated_request.assert_called_once_with(
            'GET', 'https://api.test.com/test', params={'param': 'value'}
        )

    def test_send_request_failure(self, mock_dependencies):
        """Test request failure handling"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_dependencies['client'].make_authenticated_request.return_value = mock_response
        
        handler = MarketHandler()
        result = handler._send_request('https://api.test.com/test')
        
        assert result is None

    def test_send_request_exception(self, mock_dependencies):
        """Test request exception handling"""
        mock_dependencies['client'].make_authenticated_request.side_effect = Exception('Network error')
        
        handler = MarketHandler()
        result = handler._send_request('https://api.test.com/test')
        
        assert result is None


class TestMarketHandlerQuoteMethods:
    """Test quote-related methods"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict('os.environ', {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.market_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.market_handler.SchwabClient') as mock_client_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'client_class': mock_client_class,
                'client': mock_client
            }

    def test_extract_quote_data(self, mock_dependencies):
        """Test quote data extraction"""
        response_data = {
            'AAPL': {
                'quote': {
                    'lastPrice': 150.0,
                    'bidPrice': 149.9,
                    'askPrice': 150.1,
                    'totalVolume': 1000000,
                    'netChange': 2.5,
                    'netPercentChange': 1.69,
                    'tradeTime': 1234567890
                }
            }
        }
        
        handler = MarketHandler()
        result = handler._extract_quote_data(response_data)
        
        expected = {
            'AAPL': {
                'price': 150.0,
                'bid': 149.9,
                'ask': 150.1,
                'volume': 1000000,
                'change': 2.5,
                'change_pct': 1.69,
                'timestamp': 1234567890
            }
        }
        assert result == expected

    def test_extract_quote_data_missing_fields(self, mock_dependencies):
        """Test quote data extraction with missing fields"""
        response_data = {
            'AAPL': {
                'quote': {
                    'lastPrice': 150.0,
                    # Missing other fields
                }
            }
        }
        
        handler = MarketHandler()
        result = handler._extract_quote_data(response_data)
        
        expected = {
            'AAPL': {
                'price': 150.0,
                'bid': None,
                'ask': None,
                'volume': None,
                'change': None,
                'change_pct': None,
                'timestamp': None
            }
        }
        assert result == expected

    def test_get_quotes_success(self, mock_dependencies):
        """Test successful quote retrieval"""
        mock_response = {
            'AAPL': {
                'quote': {
                    'lastPrice': 150.0,
                    'bidPrice': 149.9,
                    'askPrice': 150.1,
                    'totalVolume': 1000000,
                    'netChange': 2.5,
                    'netPercentChange': 1.69,
                    'tradeTime': 1234567890
                }
            }
        }
        
        handler = MarketHandler()
        handler._send_request = Mock(return_value=mock_response)
        
        result = handler.get_quotes(['AAPL'])
        
        assert 'AAPL' in result
        assert result['AAPL']['price'] == 150.0
        handler._send_request.assert_called_once()

    def test_get_quotes_failure(self, mock_dependencies):
        """Test quote retrieval failure"""
        handler = MarketHandler()
        handler._send_request = Mock(return_value=None)
        
        result = handler.get_quotes(['AAPL'])
        
        assert result == {}


class TestMarketHandlerPriceHistoryMethods:
    """Test price history methods"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict('os.environ', {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.market_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.market_handler.SchwabClient') as mock_client_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'client_class': mock_client_class,
                'client': mock_client
            }

    def test_get_price_history_success(self, mock_dependencies):
        """Test successful price history retrieval"""
        mock_response = {
            'symbol': 'AAPL',
            'candles': [
                {'datetime': 1234567890, 'open': 150.0, 'high': 151.0, 'low': 149.0, 'close': 150.5, 'volume': 1000000}
            ]
        }
        
        handler = MarketHandler()
        handler._send_request = Mock(return_value=mock_response)
        
        result = handler.get_price_history('AAPL', PeriodType.DAY, 1, FrequencyType.MINUTE, 5)
        
        assert result == mock_response
        handler._send_request.assert_called_once()

    def test_get_price_history_failure(self, mock_dependencies):
        """Test price history retrieval failure"""
        handler = MarketHandler()
        handler._send_request = Mock(return_value=None)
        
        result = handler.get_price_history('AAPL')
        
        assert result == {}

    def test_get_price_history_invalid_combination(self, mock_dependencies):
        """Test price history with invalid period/frequency combination"""
        handler = MarketHandler()
        
        with pytest.raises(ValueError):
            handler.get_price_history('AAPL', PeriodType.DAY, 1, FrequencyType.MONTHLY, 1)

    def test_get_option_chains_not_implemented(self, mock_dependencies):
        """Test option chains method returns empty dict"""
        handler = MarketHandler()
        result = handler.get_option_chains('AAPL')
        
        assert result == {}


class TestMarketHandlerMarketHoursMethods:
    """Test market hours methods"""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture to mock required environment variables"""
        with patch.dict('os.environ', {
            'SCHWAB_API_KEY': 'test_api_key',
            'SCHWAB_SECRET': 'test_secret',
            'SCHWAB_APP_NAME': 'test_app_name'
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        """Fixture to mock all external dependencies"""
        with patch('system.algo_trader.schwab.market_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.market_handler.SchwabClient') as mock_client_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'client_class': mock_client_class,
                'client': mock_client
            }

    def test_get_market_hours_success_open(self, mock_dependencies):
        """Test successful market hours retrieval when market is open"""
        mock_response = {
            'equity': {
                'EQ': {
                    'isOpen': True,
                    'sessionHours': {
                        'regularMarket': [
                            {'start': '2023-01-01T09:30:00-05:00', 'end': '2023-01-01T16:00:00-05:00'}
                        ]
                    }
                }
            }
        }
        
        handler = MarketHandler()
        handler._send_request = Mock(return_value=mock_response)
        
        test_date = datetime(2023, 1, 1)
        result = handler.get_market_hours(test_date)
        
        expected = {
            'date': '2023-01-01',
            'start': '2023-01-01T09:30:00-05:00',
            'end': '2023-01-01T16:00:00-05:00'
        }
        assert result == expected

    def test_get_market_hours_success_closed(self, mock_dependencies):
        """Test successful market hours retrieval when market is closed"""
        mock_response = {
            'equity': {
                'EQ': {
                    'isOpen': False,
                    'sessionHours': {
                        'regularMarket': [
                            {'start': '2023-01-01T09:30:00-05:00', 'end': '2023-01-01T16:00:00-05:00'}
                        ]
                    }
                }
            }
        }
        
        handler = MarketHandler()
        handler._send_request = Mock(return_value=mock_response)
        
        test_date = datetime(2023, 1, 1)
        result = handler.get_market_hours(test_date)
        
        expected = {'date': '2023-01-01'}
        assert result == expected

    def test_get_market_hours_failure(self, mock_dependencies):
        """Test market hours retrieval failure"""
        handler = MarketHandler()
        handler._send_request = Mock(return_value=None)
        
        test_date = datetime(2023, 1, 1)
        result = handler.get_market_hours(test_date)
        
        assert result == {}

    def test_get_market_hours_no_equity_data(self, mock_dependencies):
        """Test market hours when no equity data in response"""
        mock_response = {
            'other_market': {
                'isOpen': True
            }
        }
        
        handler = MarketHandler()
        handler._send_request = Mock(return_value=mock_response)
        
        test_date = datetime(2023, 1, 1)
        result = handler.get_market_hours(test_date)
        
        expected = {'date': '2023-01-01'}
        assert result == expected

    def test_get_market_hours_equity_format_variation(self, mock_dependencies):
        """Test market hours with different equity data format"""
        mock_response = {
            'equity': {
                'equity': {  # Different format than 'EQ'
                    'isOpen': True,
                    'sessionHours': {
                        'regularMarket': [
                            {'start': '2023-01-01T09:30:00-05:00', 'end': '2023-01-01T16:00:00-05:00'}
                        ]
                    }
                }
            }
        }
        
        handler = MarketHandler()
        handler._send_request = Mock(return_value=mock_response)
        
        test_date = datetime(2023, 1, 1)
        result = handler.get_market_hours(test_date)
        
        expected = {
            'date': '2023-01-01',
            'start': '2023-01-01T09:30:00-05:00',
            'end': '2023-01-01T16:00:00-05:00'
        }
        assert result == expected
