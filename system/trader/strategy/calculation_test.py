import pytest
import pandas as pd
from system.trader.strategy.calculation import near_support
from component.software.finance.stock.stock import Stock
from component.software.finance.timescale_enum import Timescale


@pytest.fixture
def apple_stock_data():
    """Fixture to get AAPL data once and reuse across tests"""
    stock = Stock("AAPL")
    return stock.get_historical(frequency=Timescale.DAY, period=Timescale.YEAR)


@pytest.mark.integration
def test_near_support_with_real_data(apple_stock_data):
    """Test that near_support works with real stock data and returns boolean series"""
    result = near_support(data=apple_stock_data.close, distance=20)
    
    # Basic assertions
    assert isinstance(result, pd.Series)
    assert result.dtype == bool
    assert len(result) == len(apple_stock_data.close)


@pytest.mark.integration
def test_near_support_visualization(apple_stock_data):
    """Visualize near_support function results with real stock data"""
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.signal import find_peaks
    
    # Test with parameters appropriate for daily data
    near_support_result = near_support(
        data=apple_stock_data.close, 
        distance=15,      # 15 days apart minimum (vs 8 weeks for weekly data)
        height_pct=0.1,   # 10% below median (vs 15% for weekly)  
        prominence=1.0,   # Higher prominence for daily noise filtering
        buffer=0.05,      # 5% buffer (vs 15% for weekly)
        min_lookback=60   # 60 days history (vs 20 weeks)
    )
    
    # Find actual valleys for comparison (match the function parameters)
    median_price = apple_stock_data.close.median().iloc[0] if len(apple_stock_data.close.median().shape) > 0 else apple_stock_data.close.median()
    height_threshold = median_price * (1 - 0.1)  # Match the height_pct  
    valleys, _ = find_peaks(-apple_stock_data.close.values.flatten(), 
                           distance=15, height=-height_threshold, prominence=1.0)
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # Plot price line
    ax.plot(apple_stock_data.close.index, apple_stock_data.close.values.flatten(), 
            'b-', linewidth=1, label='AAPL Close Price', alpha=0.8)
    
    # Highlight periods where near_support is True
    support_dates = near_support_result[near_support_result].index
    if len(support_dates) > 0:
        support_prices = apple_stock_data.close.loc[support_dates]
        ax.scatter(support_dates, support_prices.values.flatten(),
                  c='red', s=20, alpha=0.6, label='Near Support', zorder=5)
    
    # Mark actual valley points
    valley_prices = apple_stock_data.close.values.flatten()[valleys]
    valley_dates = apple_stock_data.close.index[valleys]
    ax.scatter(valley_dates, valley_prices, 
              c='green', s=50, marker='^', label='Support Valleys', zorder=6)
    
    # Add median line for reference
    ax.axhline(y=median_price, color='gray', linestyle='--', alpha=0.5, 
              label=f'Median Price (${median_price:.2f})')
    
    # Add height threshold line
    ax.axhline(y=height_threshold, color='orange', linestyle='--', alpha=0.5,
              label=f'Height Threshold (${height_threshold:.2f})')
    
    # Formatting
    ax.set_title('AAPL Support Level Detection Visualization', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Price ($)', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('/tmp/near_support_visualization.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # Basic validation that we found some support
    print(f"Visualization saved to: /tmp/near_support_visualization.png")
    print(f"Found {len(valleys)} support valleys")
    print(f"Near support result type: {type(near_support_result)}")
    print(f"Near support result shape: {near_support_result.shape}")
    
    no_bounce_count = int(near_support_result.sum())
    
    print(f"No bounce requirement (simplified): {no_bounce_count} periods near support")
    print("Bounce requirement removed - all detected valleys are considered valid support")
    
    assert len(valleys) > 0, "Should detect some support valleys"
