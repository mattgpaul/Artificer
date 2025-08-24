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
        assert stock_instance.get_close(Timescale.DAY.value) == 152.25
        assert stock_instance.get_close(Timescale.MINUTE.value) == 152.25
        assert type(stock_instance.get_close(Timescale.YEAR.value)) == float

    def test_get_close_invalid_timescale(self, stock_instance):
        with pytest.raises(ValueError):
            stock_instance.get_close("100y")

class TestGetOpen:
    def test_get_open(self, stock_instance):
        assert stock_instance.get_open(Timescale.DAY.value) == 150.75
        assert stock_instance.get_open(Timescale.MINUTE.value) == 150.75
        assert type(stock_instance.get_open(Timescale.YEAR.value)) == float

    def test_get_open_invalid_timescale(self, stock_instance):
        with pytest.raises(ValueError):
            stock_instance.get_open("100y")

class TestGetHigh:
    def test_get_high(self, stock_instance):
        assert stock_instance.get_high(Timescale.DAY.value) == 153.00
        assert stock_instance.get_high(Timescale.MINUTE.value) == 153.00
        assert type(stock_instance.get_high(Timescale.YEAR.value)) == float

    def test_get_high_invalid_timescale(self, stock_instance):
        with pytest.raises(ValueError):
            stock_instance.get_high("100y")

class TestGetLow:
    def test_get_low(self, stock_instance):
        assert stock_instance.get_low(Timescale.DAY.value) == 149.50
        assert stock_instance.get_low(Timescale.MINUTE.value) == 149.50
        assert type(stock_instance.get_low(Timescale.YEAR.value)) == float

    def test_get_low_invalid_timescale(self, stock_instance):
        with pytest.raises(ValueError):
            stock_instance.get_low("100y")
            