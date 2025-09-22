import pytest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from system.algo_trader.strategy.calculation import valleys


class TestCalculationIntegration:
    
    @pytest.mark.integration
    def test_valleys_integration_with_visualization(self):
        """Integration test for valleys function with realistic price data and visualization"""
        # Create realistic price data with known patterns
        np.random.seed(42)  # For reproducible results
        dates = pd.date_range('2024-01-01', periods=200, freq='D')
        
        # Generate price-like data with trend + oscillations + noise
        base_trend = np.linspace(100, 120, 200)
        oscillations = 10 * np.sin(np.arange(200) * 0.1) + 5 * np.sin(np.arange(200) * 0.3)
        noise = np.random.normal(0, 1, 200)
        prices = pd.Series(base_trend + oscillations + noise, index=dates)
        
        # Test valleys function with different parameters
        valley_default = valleys(prices)  # Default: distance=10, threshold=0.01
        valley_sensitive = valleys(prices, distance=5, threshold=0.5)
        valley_conservative = valleys(prices, distance=20, threshold=2.0)
        
        # Assertions
        assert isinstance(valley_default, pd.Series)
        assert valley_default.dtype == bool
        assert len(valley_default) == len(prices)
        
        # Conservative should find fewer valleys than sensitive
        assert valley_conservative.sum() <= valley_default.sum() <= valley_sensitive.sum()
        
        # Should find at least some valleys in oscillating data
        assert valley_default.sum() > 0
        assert valley_sensitive.sum() > 0
        
        # Valley indices should be valid
        valley_indices = prices[valley_default].index
        assert len(valley_indices) > 0
        
        # Valleys should actually be local minima (basic sanity check)
        for idx in valley_indices[:3]:  # Check first few valleys
            idx_pos = prices.index.get_loc(idx)
            if 2 <= idx_pos <= len(prices) - 3:  # Ensure we have neighbors
                neighbors = prices.iloc[idx_pos-2:idx_pos+3]
                valley_value = prices.iloc[idx_pos]
                # Valley should be among the lower values in its neighborhood
                assert valley_value <= neighbors.median()
        
        # Generate visualization for manual inspection
        plt.figure(figsize=(15, 10))
        
        # Plot 1: Price data with different valley detections
        plt.subplot(2, 1, 1)
        plt.plot(prices.index, prices, 'b-', label='Price Data', alpha=0.7)
        plt.scatter(prices[valley_sensitive].index, prices[valley_sensitive], 
                   color='lightcoral', s=50, label='Sensitive (d=5, t=0.5)', alpha=0.8)
        plt.scatter(prices[valley_default].index, prices[valley_default], 
                   color='red', s=80, label='Default (d=10, t=0.01)', alpha=0.9)
        plt.scatter(prices[valley_conservative].index, prices[valley_conservative], 
                   color='darkred', s=120, label='Conservative (d=20, t=2.0)', zorder=5)
        plt.title('Valley Detection with Different Parameters')
        plt.ylabel('Price ($)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Plot 2: Valley counts comparison
        plt.subplot(2, 1, 2)
        counts = [valley_sensitive.sum(), valley_default.sum(), valley_conservative.sum()]
        labels = ['Sensitive\n(d=5, t=0.5)', 'Default\n(d=10, t=0.01)', 'Conservative\n(d=20, t=2.0)']
        bars = plt.bar(labels, counts, color=['lightcoral', 'red', 'darkred'], alpha=0.7)
        plt.title('Number of Valleys Detected by Parameter Setting')
        plt.ylabel('Valley Count')
        
        # Add count labels on bars
        for bar, count in zip(bars, counts):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    str(count), ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Save to /tmp/ for easy access
        plot_path = '/tmp/valleys_integration_test.png'
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()  # Don't show during test run
        
        print(f"\nIntegration Test Results:")
        print(f"  Sensitive valleys: {valley_sensitive.sum()}")
        print(f"  Default valleys: {valley_default.sum()}")
        print(f"  Conservative valleys: {valley_conservative.sum()}")
        print(f"  Visualization saved: {plot_path}")
        
    @pytest.mark.integration  
    def test_valleys_edge_cases(self):
        """Test valleys function with edge case data"""
        # Test with flat data (should find no meaningful valleys)
        flat_data = pd.Series([100.0] * 50, index=pd.date_range('2024-01-01', periods=50))
        flat_valleys = valleys(flat_data, distance=5, threshold=1.0)
        assert flat_valleys.sum() == 0  # No valleys in flat data
        
        # Test with monotonic increasing data
        increasing_data = pd.Series(range(50), index=pd.date_range('2024-01-01', periods=50))
        increasing_valleys = valleys(increasing_data, distance=5, threshold=0.5)
        assert increasing_valleys.sum() == 0  # No valleys in monotonic increase
        
        # Test with very small dataset with clear valley
        small_data = pd.Series([5, 10, 2, 8, 1], index=pd.date_range('2024-01-01', periods=5))
        small_valleys = valleys(small_data, distance=1, threshold=0.5)
        # Should detect valleys (at least one)
        assert small_valleys.sum() > 0
