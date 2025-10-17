"""
Algo Trader - Phase 2: InfluxDB Integration

Entry point for collecting historical market data from Schwab API
and storing it in InfluxDB for long-term analysis.
"""
import sys
from infrastructure.logging.logger import get_logger
from system.algo_trader.clients.redis_client import AlgoTraderRedisClient
from system.algo_trader.clients.schwab_client import AlgoTraderSchwabClient
from system.algo_trader.clients.influxdb_client import AlgoTraderInfluxDBClient


def main():
    """
    Phase 2 main flow: fetch market data and store in InfluxDB.
    """
    logger = get_logger("AlgoTraderMain")
    
    # Phase 2 Configuration: 3 tickers, each with 3 period/frequency combinations
    tickers = ["AAPL", "MSFT", "GOOGL"]
    
    # Each ticker gets these period/frequency combinations (all daily or higher)
    market_data_configs = [
        {"period_type": "month", "period": 1, "frequency_type": "daily", "frequency": 1},
        {"period_type": "month", "period": 3, "frequency_type": "daily", "frequency": 1},
        {"period_type": "year", "period": 1, "frequency_type": "weekly", "frequency": 1},
    ]
    
    logger.info("Algo Trader Phase 2: Starting")
    
    # Initialize clients
    redis_client = AlgoTraderRedisClient()
    schwab_client = AlgoTraderSchwabClient(redis_client)
    influx_client = AlgoTraderInfluxDBClient()
    
    # Test Redis connection
    if not redis_client.ping():
        logger.error("Failed to connect to Redis")
        return 1
    
    logger.info("Redis connection successful")
    
    # Note: Authentication is handled automatically by schwab_client when needed
    # It will trigger OAuth2 flow if refresh token is missing or invalid
    
    # Fetch and store data for each ticker and configuration
    total_candles = 0
    successful_writes = 0
    
    for ticker in tickers:
        logger.info(f"\nProcessing ticker: {ticker}")
        
        for config in market_data_configs:
            period_type = config["period_type"]
            period = config["period"]
            frequency_type = config["frequency_type"]
            frequency = config["frequency"]
            
            logger.info(f"  Fetching {ticker} data: {period}{period_type}, {frequency}{frequency_type}")
            
            # Fetch price history from Schwab
            price_data = schwab_client.get_price_history(
                symbol=ticker,
                period_type=period_type,
                period=period,
                frequency_type=frequency_type,
                frequency=frequency
            )
            
            if not price_data or 'candles' not in price_data:
                logger.warning(f"  No data retrieved for {ticker}")
                continue
            
            candles = price_data['candles']
            logger.info(f"  Retrieved {len(candles)} candles for {ticker}")
            
            # Write to InfluxDB
            success = influx_client.write_candle_data(
                ticker=ticker,
                period_type=period_type,
                period=period,
                frequency_type=frequency_type,
                frequency=frequency,
                candles=candles
            )
            
            if success:
                successful_writes += 1
                total_candles += len(candles)
            else:
                logger.error(f"  Failed to write {ticker} data to InfluxDB")
    
    # Summary
    expected_writes = len(tickers) * len(market_data_configs)
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 2 Summary:")
    logger.info(f"  Tickers processed: {len(tickers)}")
    logger.info(f"  Successful writes: {successful_writes}/{expected_writes}")
    logger.info(f"  Total candles stored: {total_candles}")
    logger.info(f"{'='*60}")
    
    # Close InfluxDB connection
    influx_client.close()
    
    if successful_writes == expected_writes:
        logger.info("Phase 2 completed successfully")
        print("\nPhase 2 completed successfully!")
        return 0
    else:
        logger.error(f"Phase 2 completed with errors ({successful_writes}/{expected_writes} successful)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
