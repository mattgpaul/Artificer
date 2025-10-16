"""
Algo Trader - Phase 1: Schwab API Authentication and Market Data

Entry point for testing Schwab API authentication and historical
market data retrieval using Redis for token storage.
"""
import sys
import json
from infrastructure.logging.logger import get_logger
from system.algo_trader.clients.redis_client import AlgoTraderRedisClient
from system.algo_trader.clients.schwab_client import AlgoTraderSchwabClient


def format_price_history(data: dict, ticker: str) -> str:
    """
    Format price history data for console display.
    
    Arguments:
        data: Price history response from Schwab API
        ticker: Stock ticker symbol
        
    Returns:
        Formatted string for display
    """
    if not data or 'candles' not in data:
        return f"No price history data available for {ticker}"
    
    candles = data['candles']
    if not candles:
        return f"No candles data for {ticker}"
    
    lines = [f"\n{'='*60}"]
    lines.append(f"Price History for {ticker.upper()}")
    lines.append(f"Total candles: {len(candles)}")
    lines.append(f"{'='*60}\n")
    
    # Show first 5 and last 5 candles
    display_candles = candles[:5] + candles[-5:] if len(candles) > 10 else candles
    
    for candle in display_candles:
        timestamp = candle.get('datetime', 'N/A')
        open_price = candle.get('open', 0)
        high = candle.get('high', 0)
        low = candle.get('low', 0)
        close = candle.get('close', 0)
        volume = candle.get('volume', 0)
        
        lines.append(f"Date: {timestamp}")
        lines.append(f"  Open: ${open_price:.2f}  High: ${high:.2f}  Low: ${low:.2f}  Close: ${close:.2f}")
        lines.append(f"  Volume: {volume:,}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    """
    Phase 1 main flow: authenticate and retrieve market data.
    """
    logger = get_logger("AlgoTraderMain")
    
    # Configuration
    ticker = "AAPL"  # Default ticker for testing
    period_type = "month"
    period = 1
    frequency_type = "daily"
    frequency = 1
    
    logger.info("Algo Trader Phase 1: Starting")
    
    # Initialize clients
    redis_client = AlgoTraderRedisClient()
    schwab_client = AlgoTraderSchwabClient(redis_client)
    
    # Test Redis connection
    if not redis_client.ping():
        logger.error("Failed to connect to Redis")
        return 1
    
    logger.info("Redis connection successful")
    
    # Check if we have a refresh token
    refresh_token = redis_client.get_refresh_token()
    
    if not refresh_token:
        logger.info("No refresh token found, initiating authentication flow")
        success = schwab_client.authenticate()
        if not success:
            logger.error("Authentication failed")
            return 1
    
    # Attempt to get price history
    logger.info(f"Fetching price history for {ticker}")
    price_data = schwab_client.get_price_history(
        symbol=ticker,
        period_type=period_type,
        period=period,
        frequency_type=frequency_type,
        frequency=frequency
    )
    
    if price_data:
        # Format and print results
        output = format_price_history(price_data, ticker)
        print(output)
        logger.info("Phase 1 completed successfully")
        return 0
    else:
        logger.error("Failed to retrieve price history")
        return 1


if __name__ == "__main__":
    sys.exit(main())

