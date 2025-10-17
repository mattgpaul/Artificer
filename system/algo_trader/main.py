"""
Algo Trader - Phase 3: SEC Ticker List

Entry point for collecting historical market data from Schwab API,
fetching ticker list from SEC, and storing both in InfluxDB for
long-term analysis.
"""
import sys
from infrastructure.logging.logger import get_logger
from system.algo_trader.clients.redis_client import AlgoTraderRedisClient
from system.algo_trader.clients.schwab_client import AlgoTraderSchwabClient
from system.algo_trader.clients.influxdb_client import AlgoTraderInfluxDBClient
from system.algo_trader.datasources.sec import SECDataSource


def main():
    """
    Phase 3 main flow: fetch SEC ticker list and market data, store in InfluxDB.
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
    
    logger.info("Algo Trader Phase 3: Starting")
    
    # Initialize clients
    redis_client = AlgoTraderRedisClient()
    schwab_client = AlgoTraderSchwabClient(redis_client)
    influx_client = AlgoTraderInfluxDBClient()
    sec_source = SECDataSource(influxdb_client=influx_client)
    
    # Test Redis connection
    if not redis_client.ping():
        logger.error("Failed to connect to Redis")
        return 1
    
    logger.info("Redis connection successful")
    
    # Phase 3: Fetch and store SEC ticker list
    logger.info("\n" + "="*60)
    logger.info("Phase 3: Fetching SEC Ticker List")
    logger.info("="*60)
    
    sec_tickers = sec_source.fetch_tickers()
    if sec_tickers is None:
        logger.error("Failed to fetch SEC ticker list")
        return 1
    
    logger.info(f"Fetched {len(sec_tickers)} tickers from SEC")
    
    # Store tickers in InfluxDB
    if sec_source.store_tickers_in_influxdb(sec_tickers):
        logger.info(f"Successfully stored ticker metadata in InfluxDB")
        
        # Query a few tickers to demonstrate filtering capability
        test_symbols = ["AAPL", "MSFT", "GOOGL"]
        logger.info("\nVerifying ticker metadata storage:")
        for symbol in test_symbols:
            sql = f"SELECT ticker, cik, title FROM ticker_metadata WHERE ticker = '{symbol}' LIMIT 1"
            result = influx_client.query(sql)
            if result is not None and len(result) > 0:
                # PyArrow Table: access columns directly
                cik = result.column('cik')[0].as_py()
                title = result.column('title')[0].as_py()
                logger.info(f"  {symbol}: CIK={cik}, Title={title}")
    else:
        logger.error("Failed to store SEC ticker list in InfluxDB")
        return 1
    
    # Note: Authentication is handled automatically by schwab_client when needed
    # It will trigger OAuth2 flow if refresh token is missing or invalid
    
    logger.info("\n" + "="*60)
    logger.info("Phase 2: Fetching Market Data")
    logger.info("="*60)
    
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
    logger.info(f"Phase 3 Summary:")
    logger.info(f"  SEC tickers fetched: {len(sec_tickers)}")
    logger.info(f"  Ticker metadata stored: True")
    logger.info(f"  Market data tickers processed: {len(tickers)}")
    logger.info(f"  Successful market data writes: {successful_writes}/{expected_writes}")
    logger.info(f"  Total candles stored: {total_candles}")
    logger.info(f"{'='*60}")
    
    # Demonstrate filtering capability
    logger.info("\nDemonstrating ticker filtering capability:")
    logger.info("Querying market data for tickers in SEC list...")
    for ticker in tickers:
        # Check if ticker exists in metadata
        sql = f"SELECT ticker FROM ticker_metadata WHERE ticker = '{ticker}' LIMIT 1"
        metadata = influx_client.query(sql)
        
        if metadata is not None and len(metadata) > 0:
            # Query market data for this ticker
            sql = f"SELECT COUNT(*) as count FROM market_data WHERE ticker = '{ticker}'"
            candle_count = influx_client.query(sql)
            if candle_count is not None and len(candle_count) > 0:
                # PyArrow Table: access column values
                count = candle_count.column('count')[0].as_py()
                logger.info(f"  {ticker}: Found in SEC list, {count} candles in database")
    
    # Close InfluxDB connection
    influx_client.close()
    
    if successful_writes == expected_writes:
        logger.info("Phase 3 completed successfully")
        print("\nPhase 3 completed successfully!")
        return 0
    else:
        logger.error(f"Phase 3 completed with errors ({successful_writes}/{expected_writes} successful)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
