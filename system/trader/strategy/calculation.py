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

def valleys(data: pd.Series, distance: int = 10, threshold: float = 0.01) -> pd.Series:
    """
    Find valleys (local minima) in a time series using find_peaks on inverted data.
    
    Args:
        data: Time series data to analyze
        distance: Minimum distance between valleys (in data points, default: 10)
        threshold: Minimum vertical distance to neighboring samples (relative depth requirement, default: 0.01)
    
    Returns:
        Boolean Series indicating valley locations
    """
    # Invert the data to find valleys as peaks
    inverted_data = -data
    
    # Find peaks in the inverted data (which are valleys in original data)
    valley_indices, _ = find_peaks(inverted_data, distance=distance, threshold=threshold)
    
    # Create boolean series marking valley locations
    valley_mask = pd.Series(False, index=data.index)
    if len(valley_indices) > 0:
        valley_mask.iloc[valley_indices] = True
    
    return valley_mask
