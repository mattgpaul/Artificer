import pytest
import pandas as pd
from component.software.finance.stock.stock import Stock


@pytest.fixture
def mock_yfinance_ticker(mocker):
    """Fixture that mocks yfinance Ticker and returns the mock"""
    mock_yf_instance = mocker.MagicMock()
    mock_ticker = mocker.patch('component.software.finance.stock.stock.yf.Ticker')
    mock_ticker.return_value = mock_yf_instance
    return mock_ticker, mock_yf_instance


@pytest.fixture
def sample_ticker():
    """Fixture that provides a sample ticker symbol for testing"""
    return "AAPL"


@pytest.fixture
def sample_stock_data():
    """Fixture that provides sample stock data for testing"""
    return pd.DataFrame({
        'Open': [150.0, 151.0, 149.0],
        'High': [152.0, 153.0, 151.0],
        'Low': [148.0, 149.0, 147.0],
        'Close': [151.0, 150.0, 150.5],
        'Volume': [1000000, 1100000, 950000]
    })


@pytest.fixture  
def stock_instance(mock_yfinance_ticker, sample_ticker):
    """Fixture that creates a Stock instance with mocked yfinance"""
    mock_ticker, mock_yf_instance = mock_yfinance_ticker
    stock = Stock(sample_ticker)
    return stock, mock_ticker, mock_yf_instance


class TestStockInitialization:
    """Test the initialization of the Stock class"""

    def test_initialize_with_valid_ticker(self, stock_instance, sample_ticker):
        """Test that Stock initializes correctly with a valid ticker symbol"""
        stock, mock_ticker, mock_yf_instance = stock_instance
        
        assert stock.ticker == sample_ticker
        assert stock.data == mock_yf_instance
        assert stock.logger is not None
        assert hasattr(stock, 'logger')

    def test_exception_with_invalid_ticker(self, mocker):
        """
        Test that initializing Stock with an invalid ticker like '1234' raises an exception
        when attempting to retrieve its name.
        """
        mock_ticker = mocker.patch('component.software.finance.stock.stock.yf.Ticker')
        mock_yf_instance = mocker.MagicMock()
        mock_yf_instance.info = {}
        mock_ticker.return_value = mock_yf_instance

        stock = Stock("1234")
        with pytest.raises(Exception):
            stock.get_name()

class TestStockDataRetrieval:
    """Test the data retrieval of the Stock class"""

    def test_get_open(self):
        failure = 2
        assert failure == 4

    def test_get_close(self):
        pass

    def test_get_high(self):
        pass

    def test_get_low(self):
        pass

    def test_get_name(self):
        pass

    def test_exception_with_invalid_timescale(self):
        pass

    def test_exception_with_invalid_ticker(self):
        pass

    def test_different_timescales(self):
        pass

    def test_yfinance_integration_mock(self):
        pass