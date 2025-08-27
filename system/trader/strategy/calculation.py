import pandas as pd
from scipy.signal import find_peaks
import numpy as np

def sma(data: pd.Series, period: int) -> pd.Series:
    return data.rolling(window=period).mean()

def ema(data: pd.Series, period: int) -> pd.Series:
    return data.ewm(span=period, adjust=False).mean()

def atr(data: pd.Series, period: int) -> pd.Series:
    high_low = data['High'] - data['Low']
    high_close = (data['High'] - data['Close'].shift(1)).abs()
    low_close = (data['Low'] - data['Close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def near_support(data: pd.Series, distance: int, height_pct: float = 0.5, prominence=None, buffer: float = 0.02, min_lookback: int = 50) -> pd.Series:
    """
    Forward-looking support detection - no look-ahead bias
    
    Args:
        data: Price series
        distance: Minimum distance between valleys
        height_pct: Percentage below median for height threshold
        prominence: Minimum prominence for valleys
        buffer: Price tolerance for "near" support

        min_lookback: Minimum periods of history needed
    
    Returns:
        Boolean series - True where current price is near confirmed historical support
    """
    result = pd.Series(False, index=data.index)
    
    for i in range(min_lookback, len(data)):
        current_price = data.iloc[i]
        historical_data = data.iloc[:i]
        
        median_price = historical_data.median()
        height_threshold = median_price * (1 - height_pct)
        
        valleys, _ = find_peaks(-historical_data.values, distance=distance, 
                               height=-height_threshold, prominence=prominence)
        
        if len(valleys) == 0:
            continue
            
        confirmed_support = []
        for valley_idx in valleys:
            valley_price = historical_data.iloc[valley_idx]
            confirmed_support.append(valley_price)
        
        if confirmed_support:
            support_array = np.array(confirmed_support)
            price_diffs = np.abs(current_price - support_array) / support_array
            result.iloc[i] = np.any(price_diffs <= buffer)
    
    return result
