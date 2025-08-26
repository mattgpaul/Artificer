import pytest
from component.software.finance.stock.stock import Stock
from component.software.finance.timescale_enum import Timescale


@pytest.mark.integration
def test_stock_fetches_real_data():
    """Integration test - fetches actual data, no mocking"""
    # Create stock instance
    stock = Stock("AAPL")
    
    # Test basic properties
    assert stock.ticker == "AAPL"
    
    # Fetch real historical data  
    historical = stock.get_historical(Timescale.DAY, Timescale.YEAR)
    assert historical.ticker == "AAPL"
    assert len(historical.data) > 0  # Should have some data
    assert len(historical.close) > 0  # Should have closing prices

    print(f"Historical data: {len(historical.data)}")