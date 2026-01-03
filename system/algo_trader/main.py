"""
Algo Trader - Phase 4: Grafana Visualization

Entry point for collecting historical market data from Schwab API,
fetching ticker list from SEC, storing both in InfluxDB, and
setting up Grafana visualization for long-term analysis.
"""
import sys
from infrastructure.logging.logger import get_logger
from system.algo_trader.clients.redis_client import AlgoTraderRedisClient
from system.algo_trader.clients.schwab_client import AlgoTraderSchwabClient
from system.algo_trader.clients.influxdb_client import AlgoTraderInfluxDBClient
from system.algo_trader.clients.grafana_client import AlgoTraderGrafanaClient
from system.algo_trader.datasources.sec import SECDataSource


def main():
    """
    Phase 4 main flow: fetch SEC ticker list, collect market data for 8 tickers,
    store in InfluxDB, and set up Grafana visualization.
    """
    logger = get_logger("AlgoTraderMain")
    
    # Phase 4 Configuration: 8 tickers (5 random + 3 known), each with 3 timeframes
    known_tickers = ["AAPL", "MSFT", "GOOGL"]
    
    # Phase 4 timeframes as specified: 1d:5yr, 1wk:10yr, 1mo:20yr
    market_data_configs = [
        {"period_type": "year", "period": 5, "frequency_type": "daily", "frequency": 1},      # 1d:5yr
        {"period_type": "year", "period": 10, "frequency_type": "weekly", "frequency": 1},   # 1wk:10yr  
        {"period_type": "year", "period": 20, "frequency_type": "monthly", "frequency": 1},  # 1mo:20yr
    ]
    
    logger.info("Algo Trader Phase 4: Starting")
    
    # Initialize clients
    redis_client = AlgoTraderRedisClient()
    schwab_client = AlgoTraderSchwabClient(redis_client)
    influx_client = AlgoTraderInfluxDBClient()
    grafana_client = AlgoTraderGrafanaClient()
    sec_source = SECDataSource(influxdb_client=influx_client)
    
    # Test Redis connection
    if not redis_client.ping():
        logger.error("Failed to connect to Redis")
        return 1
    
    logger.info("Redis connection successful")
    
    # Phase 4: Fetch SEC ticker list and select random tickers
    logger.info("\n" + "="*60)
    logger.info("Phase 4: Fetching SEC Ticker List and Selecting Random Tickers")
    logger.info("="*60)
    
    sec_tickers = sec_source.fetch_tickers()
    if sec_tickers is None:
        logger.error("Failed to fetch SEC ticker list")
        return 1
    
    logger.info(f"Fetched {len(sec_tickers)} tickers from SEC")
    
    # Store tickers in InfluxDB
    if sec_source.store_tickers_in_influxdb(sec_tickers):
        logger.info(f"Successfully stored ticker metadata in InfluxDB")
        
        # Select 5 random tickers from SEC data (excluding known tickers)
        import random
        sec_symbols = [ticker['ticker'] for ticker in sec_tickers if ticker['ticker'] not in known_tickers]
        random_tickers = random.sample(sec_symbols, min(5, len(sec_symbols)))
        
        # Combine known and random tickers
        all_tickers = known_tickers + random_tickers
        logger.info(f"Selected tickers for Phase 4:")
        logger.info(f"  Known tickers: {known_tickers}")
        logger.info(f"  Random tickers: {random_tickers}")
        logger.info(f"  Total tickers: {len(all_tickers)}")
        
    else:
        logger.error("Failed to store SEC ticker list in InfluxDB")
        return 1
    
    # Note: Authentication is handled automatically by schwab_client when needed
    # It will trigger OAuth2 flow if refresh token is missing or invalid
    
    logger.info("\n" + "="*60)
    logger.info("Phase 4: Fetching Market Data for 8 Tickers")
    logger.info("="*60)
    
    # Fetch and store data for each ticker and configuration
    total_candles = 0
    successful_writes = 0
    
    for ticker in all_tickers:
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
    expected_writes = len(all_tickers) * len(market_data_configs)
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 4 Summary:")
    logger.info(f"  SEC tickers fetched: {len(sec_tickers)}")
    logger.info(f"  Ticker metadata stored: True")
    logger.info(f"  Market data tickers processed: {len(all_tickers)}")
    logger.info(f"  Known tickers: {known_tickers}")
    logger.info(f"  Random tickers: {random_tickers}")
    logger.info(f"  Successful market data writes: {successful_writes}/{expected_writes}")
    logger.info(f"  Total candles stored: {total_candles}")
    logger.info(f"{'='*60}")
    
    # Demonstrate filtering capability
    logger.info("\nDemonstrating ticker filtering capability:")
    logger.info("Querying market data for tickers in SEC list...")
    for ticker in all_tickers:
        # Check if ticker exists in metadata
        sql = f"SELECT ticker FROM ticker_metadata WHERE ticker = '{ticker}' LIMIT 1"
        metadata = influx_client.query(sql)
        
        if metadata is not None and len(metadata) > 0:
            # Query market data for this ticker
            sql = f"SELECT COUNT(*) as count FROM market_data WHERE ticker = '{ticker}'"
            candle_count = influx_client.query(sql)
            if candle_count is not None and len(candle_count) > 0:
                # Pandas DataFrame: use iloc to access rows
                count = candle_count.iloc[0]['count']
                logger.info(f"  {ticker}: Found in SEC list, {count} candles in database")
    
    # Close InfluxDB connection
    influx_client.close()
    
    # Phase 4: Setup Grafana Visualization
    logger.info("\n" + "="*60)
    logger.info("Phase 4: Setting up Grafana Visualization")
    logger.info("="*60)
    
    if grafana_client.setup_visualization():
        logger.info("Grafana visualization setup completed successfully")
        dashboard_url = grafana_client.get_dashboard_url()
        logger.info(f"Access your market data dashboard at: {dashboard_url}")
        logger.info(f"Grafana admin interface: {grafana_client.host}")
        logger.info(f"Admin credentials: {grafana_client.admin_user} / {grafana_client.admin_password}")
    else:
        logger.error("Failed to setup Grafana visualization")
        return 1
    
    if successful_writes == expected_writes:
        logger.info("Phase 4 completed successfully")
        print("\nPhase 4 completed successfully!")
        print(f"View your market data at: {grafana_client.get_dashboard_url()}")
        return 0
    else:
        logger.error(f"Phase 4 completed with errors ({successful_writes}/{expected_writes} successful)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
