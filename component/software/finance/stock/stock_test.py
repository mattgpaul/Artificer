import pytest
from component.software.finance.stock.stock import Stock
from component.software.finance.timescale_enum import Timescale

@pytest.fixture(scope="session")
def stock_instance():
    return Stock(ticker="AAPL")

@pytest.fixture(scope="session")
def stock_data():
    # TODO: Mock the data
    # Assume a simple dictionary structure for now
    return {
            "open": 150.75,
            "close": 152.25,
            "high": 153.00,
            "low": 149.50,
            "volume": 1000000,
        }

class TestStockInstance:
    def test_instance_creation(self, stock_instance):
        assert type(stock_instance) is Stock
        assert stock_instance.ticker == "AAPL"
        assert stock_instance.logger is not None

class TestRequestHandler:
    pass

class TestGetClose:
    def test_get_close(self, stock_instance):
        assert stock_instance.get_close(Timescale.DAY) == 152.25
        assert stock_instance.get_close(Timescale.MINUTE) == 152.25
        assert type(stock_instance.get_close(Timescale.YEAR)) == float

class TestGetOpen:
    def test_get_open(self, stock_instance):
        assert stock_instance.get_open(Timescale.DAY) == 150.75
        assert stock_instance.get_open(Timescale.MINUTE) == 150.75
        assert type(stock_instance.get_open(Timescale.YEAR)) == float

class TestGetHigh:
    def test_get_high(self, stock_instance):
        assert stock_instance.get_high(Timescale.DAY) == 153.00
        assert stock_instance.get_high(Timescale.MINUTE) == 153.00
        assert type(stock_instance.get_high(Timescale.YEAR)) == float

class TestGetLow:
    def test_get_low(self, stock_instance):
        assert stock_instance.get_low(Timescale.DAY) == 149.50
        assert stock_instance.get_low(Timescale.MINUTE) == 149.50
        assert type(stock_instance.get_low(Timescale.YEAR)) == float

            