import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from system.algo_trader.strategy.base_strategy import BaseStrategy
from infrastructure.logging.logger import get_logger


class NearSupport(BaseStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.position = 0
        
        # Default parameters
        defaults = {
            'distance': 15,
            'height_pct': 0.1,
            'prominence': 1.0,
            'buffer': 0.05,
            'min_lookback': 60
        }
        self.config = self.get_strategy_config(defaults)

    def near_support(self, data: pd.Series, distance: int = 15, height_pct: float = 0.1,
                    prominence: float = 1.0, buffer: float = 0.05, min_lookback: int = 60) -> bool:
        """
        Check if current price (last value) is near support levels
        
        Returns:
            Boolean - True if current price is near a support level
        """
        if len(data) < min_lookback:
            return False
            
        current_price = data.iloc[-1]
        
        median_price = data.median()
        height_threshold = median_price * (1 - height_pct)
        
        # Find valleys in all data (including current price)
        valleys, _ = find_peaks(-data.values, distance=distance,
                               height=-height_threshold, prominence=prominence)
        
        if len(valleys) == 0:
            return False
        
        # Check if current price is near any support level
        support_prices = data.iloc[valleys]
        price_diffs = np.abs(current_price - support_prices) / support_prices
        
        return np.any(price_diffs <= buffer)

    @property
    def buy(self) -> bool:
        """Check if current price is near support - buy signal"""
        return self.near_support(self.stock.close, **self.config)

    @property
    def sell(self) -> bool:
        return False  # TODO: Implement sell logic
