"""
Unit tests for AccountHandler - Account API Methods

Tests cover account retrieval, positions, orders, and trading operations.
All external dependencies are mocked to avoid network calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from system.algo_trader.schwab.account_handler import AccountHandler


class TestAccountHandlerInitialization:
    """Test AccountHandler initialization"""

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
        with patch('system.algo_trader.schwab.account_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker
            }

    def test_initialization_success(self, mock_dependencies):
        """Test successful AccountHandler initialization"""
        handler = AccountHandler()
        
        assert handler.account_url == "https://api.schwabapi.com/trader/v1"
        assert handler.logger is not None
        assert handler.api_key == 'test_api_key'
        assert handler.secret == 'test_secret'


class TestAccountHandlerAccountMethods:
    """Test account information retrieval methods"""

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
        with patch('system.algo_trader.schwab.account_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker
            }

    def test_get_accounts_success(self, mock_dependencies):
        """Test successful accounts retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'accountNumber': '123456',
                'type': 'MARGIN',
                'accountBalance': {'totalEquity': 50000.00}
            }
        ]
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_accounts()
        
        assert len(result) == 1
        assert result[0]['accountNumber'] == '123456'
        handler.make_authenticated_request.assert_called_once_with(
            'GET', 'https://api.schwabapi.com/trader/v1/accounts'
        )

    def test_get_accounts_failure(self, mock_dependencies):
        """Test accounts retrieval failure"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_accounts()
        
        assert result == {}

    def test_get_account_details_success(self, mock_dependencies):
        """Test successful account details retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'accountNumber': '123456',
            'type': 'MARGIN',
            'roundTrips': 0,
            'accountBalance': {
                'totalEquity': 50000.00,
                'cashAvailable': 10000.00
            }
        }
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_account_details('123456')
        
        assert result['accountNumber'] == '123456'
        assert result['accountBalance']['totalEquity'] == 50000.00
        handler.make_authenticated_request.assert_called_once_with(
            'GET', 'https://api.schwabapi.com/trader/v1/accounts/123456'
        )

    def test_get_account_details_failure(self, mock_dependencies):
        """Test account details retrieval failure"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = 'Account not found'
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_account_details('999999')
        
        assert result == {}


class TestAccountHandlerPositionMethods:
    """Test position retrieval methods"""

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
        with patch('system.algo_trader.schwab.account_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker
            }

    def test_get_positions_success(self, mock_dependencies):
        """Test successful positions retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'positions': [
                {
                    'instrument': {'symbol': 'AAPL', 'assetType': 'EQUITY'},
                    'longQuantity': 100,
                    'averagePrice': 150.00
                }
            ]
        }
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_positions('123456')
        
        assert 'positions' in result
        assert result['positions'][0]['instrument']['symbol'] == 'AAPL'
        handler.make_authenticated_request.assert_called_once_with(
            'GET', 'https://api.schwabapi.com/trader/v1/accounts/123456/positions'
        )

    def test_get_positions_failure(self, mock_dependencies):
        """Test positions retrieval failure"""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = 'Forbidden'
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_positions('123456')
        
        assert result == {}

    def test_get_positions_empty(self, mock_dependencies):
        """Test positions retrieval with no positions"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'positions': []}
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_positions('123456')
        
        assert result['positions'] == []


class TestAccountHandlerOrderMethods:
    """Test order management methods"""

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
        with patch('system.algo_trader.schwab.account_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker
            }

    def test_get_orders_success(self, mock_dependencies):
        """Test successful orders retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'orderId': 'ORD123',
                'status': 'WORKING',
                'orderType': 'LIMIT',
                'quantity': 100
            }
        ]
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_orders('123456')
        
        assert len(result) == 1
        assert result[0]['orderId'] == 'ORD123'
        handler.make_authenticated_request.assert_called_once_with(
            'GET', 'https://api.schwabapi.com/trader/v1/accounts/123456/orders'
        )

    def test_get_orders_failure(self, mock_dependencies):
        """Test orders retrieval failure"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.get_orders('123456')
        
        assert result == {}

    def test_place_order_success(self, mock_dependencies):
        """Test successful order placement"""
        order_data = {
            'orderType': 'LIMIT',
            'session': 'NORMAL',
            'duration': 'DAY',
            'orderStrategyType': 'SINGLE',
            'orderLegCollection': [
                {
                    'instruction': 'BUY',
                    'quantity': 100,
                    'instrument': {'symbol': 'AAPL', 'assetType': 'EQUITY'}
                }
            ],
            'price': 150.00
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'orderId': 'ORD456'}
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.place_order('123456', order_data)
        
        assert result['orderId'] == 'ORD456'
        handler.make_authenticated_request.assert_called_once_with(
            'POST', 'https://api.schwabapi.com/trader/v1/accounts/123456/orders',
            json=order_data
        )

    def test_place_order_failure(self, mock_dependencies):
        """Test order placement failure"""
        order_data = {'invalid': 'data'}
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid order data'
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.place_order('123456', order_data)
        
        assert result == {}

    def test_cancel_order_success(self, mock_dependencies):
        """Test successful order cancellation"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.cancel_order('123456', 'ORD789')
        
        assert result is True
        handler.make_authenticated_request.assert_called_once_with(
            'DELETE', 'https://api.schwabapi.com/trader/v1/accounts/123456/orders/ORD789'
        )

    def test_cancel_order_failure(self, mock_dependencies):
        """Test order cancellation failure"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = 'Order not found'
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.cancel_order('123456', 'INVALID')
        
        assert result is False

    def test_cancel_order_already_filled(self, mock_dependencies):
        """Test cancelling an already filled order"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Order already filled'
        
        handler = AccountHandler()
        handler.make_authenticated_request = Mock(return_value=mock_response)
        
        result = handler.cancel_order('123456', 'ORD999')
        
        assert result is False


class TestAccountHandlerIntegration:
    """Test integration scenarios with multiple operations"""

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
        with patch('system.algo_trader.schwab.account_handler.get_logger') as mock_logger, \
             patch('system.algo_trader.schwab.schwab_client.AccountBroker') as mock_broker_class:
            
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker
            
            yield {
                'logger': mock_logger,
                'logger_instance': mock_logger_instance,
                'broker_class': mock_broker_class,
                'broker': mock_broker
            }

    def test_full_trading_workflow(self, mock_dependencies):
        """Test complete trading workflow: check account -> check positions -> place order"""
        handler = AccountHandler()
        
        # Step 1: Get account details
        account_response = MagicMock()
        account_response.status_code = 200
        account_response.json.return_value = {
            'accountNumber': '123456',
            'accountBalance': {'cashAvailable': 10000.00}
        }
        
        # Step 2: Get positions
        positions_response = MagicMock()
        positions_response.status_code = 200
        positions_response.json.return_value = {'positions': []}
        
        # Step 3: Place order
        order_response = MagicMock()
        order_response.status_code = 201
        order_response.json.return_value = {'orderId': 'ORD123'}
        
        handler.make_authenticated_request = Mock(
            side_effect=[account_response, positions_response, order_response]
        )
        
        # Execute workflow
        account = handler.get_account_details('123456')
        assert account['accountBalance']['cashAvailable'] == 10000.00
        
        positions = handler.get_positions('123456')
        assert positions['positions'] == []
        
        order_data = {'orderType': 'MARKET', 'quantity': 10}
        order = handler.place_order('123456', order_data)
        assert order['orderId'] == 'ORD123'
        
        assert handler.make_authenticated_request.call_count == 3

