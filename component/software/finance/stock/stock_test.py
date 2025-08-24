import pytest
from datetime import datetime
from component.software.finance.stock.stock import Stock
from component.software.finance.timescale_enum import Timescale

@pytest.fixture(scope="session")
def stock_instance():
    return Stock(ticker="AAPL")

@pytest.fixture
def mock_get_data(mocker, stock_data):
    """Mock the _get_data method to return controlled test data"""
    mock = mocker.patch.object(Stock, "_get_data", return_value=stock_data)
    return mock  # Return the mock so tests can use it

@pytest.fixture(scope="session")
def stock_data():
    # TODO: Mock the data
    # Assume a simple dictionary structure for now
    return {
            "open": 150.75,
            "close": 155.25,
            "high": 155.25,
            "low": 149.75,
            "volume": 1000000,
        }

@pytest.fixture(scope="session")
def historical_data():
    return {
        datetime(2025, 8, 4, 13, 30, 0).timestamp(): {  # Market open in UTC
            "open": 150.75,
            "close": 152.25,
            "high": 153.00,
            "low": 149.50,
            "volume": 500,
        },
        datetime(2025, 8, 4, 20, 0, 0).timestamp(): {  # Market close in UTC
            "open": 150.75,
            "close": 152.25,
            "high": 153.00,
            "low": 149.50,
            "volume": 1000000,
        },
    }

class TestStockInstance:
    def test_instance_creation(self, stock_instance):
        assert type(stock_instance) is Stock
        assert stock_instance.ticker == "AAPL"
        assert stock_instance.logger is not None

class TestRequestHandler:
    pass

class TestGetClose:
    def test_get_close(self, stock_instance, mock_get_data):
        assert stock_instance.get_close(Timescale.DAY) == 155.25
        assert stock_instance.get_close(Timescale.MINUTE) == 155.25
        assert type(stock_instance.get_close(Timescale.YEAR)) == float

class TestGetOpen:
    def test_get_open(self, stock_instance, mock_get_data):
        assert stock_instance.get_open(Timescale.DAY) == 150.75
        assert stock_instance.get_open(Timescale.MINUTE) == 150.75
        assert type(stock_instance.get_open(Timescale.YEAR)) == float

class TestGetHigh:
    def test_get_high(self, stock_instance, mock_get_data):
        assert stock_instance.get_high(Timescale.DAY) == 155.25
        assert stock_instance.get_high(Timescale.MINUTE) == 155.25
        assert type(stock_instance.get_high(Timescale.YEAR)) == float

class TestGetLow:
    def test_get_low(self, stock_instance, mock_get_data):
        assert stock_instance.get_low(Timescale.DAY) == 149.75
        assert stock_instance.get_low(Timescale.MINUTE) == 149.75
        assert type(stock_instance.get_low(Timescale.YEAR)) == float

class TestGetVolume:
    def test_get_volume(self, stock_instance, mock_get_data):
        assert stock_instance.get_volume(Timescale.DAY) == 1000000
        assert stock_instance.get_volume(Timescale.MINUTE) == 1000000
        assert type(stock_instance.get_volume(Timescale.YEAR)) == int

# class TestGetHistoricalData:
#     def test_get_historical_data(self, stock_instance, historical_data):
        