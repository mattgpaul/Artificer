import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from influxdb_client_3 import Point
from infrastructure.clients.influxdb_client import BaseInfluxDBClient
from infrastructure.logging.logger import get_logger


class AlgoTraderInfluxDBClient(BaseInfluxDBClient):
    """
    InfluxDB client for the algo_trader system.
    
    Handles storage of historical market data organized by ticker symbol.
    Data is tagged with ticker, period, and frequency for flexible querying.
    """
    
    def __init__(self, auto_start: bool = False):
        """
        Initialize AlgoTrader InfluxDB client.
        
        Reads configuration from environment variables with fallback:
        - System-specific (algo_trader.env) variables tried first
        - Falls back to infrastructure defaults (artificer.env)
        
        Required environment variables:
        - ALGO_TRADER_INFLUXDB_HOST from algo_trader.env (or INFLUXDB3_HTTP_BIND_ADDR)
        - INFLUXDB3_PORT from artificer.env
        - ALGO_TRADER_INFLUXDB_DATABASE from algo_trader.env
        - INFLUXDB3_AUTH_TOKEN from artificer.env (empty string if auth disabled)
        - INFLUXDB3_CONTAINER_NAME from artificer.env
        
        Arguments:
            auto_start: If True, automatically ensure container is running.
                       If False, only initialize configuration.
        """
        # Load InfluxDB configuration (system-specific → artificer.env fallback)
        host_with_port = os.getenv("ALGO_TRADER_INFLUXDB_HOST", os.getenv("INFLUXDB3_HTTP_BIND_ADDR", "localhost:8181"))
        
        # Parse host and port
        if ':' in host_with_port:
            host, port_str = host_with_port.rsplit(':', 1)
            port = int(port_str)
        else:
            host = host_with_port
            port = int(os.getenv("INFLUXDB3_PORT", "8181"))
        
        database = os.getenv("ALGO_TRADER_INFLUXDB_DATABASE", "algo-trader-database")
        token = os.getenv("INFLUXDB3_AUTH_TOKEN", "")
        container_name = os.getenv("INFLUXDB3_CONTAINER_NAME", "algo-trader-influxdb")
        
        # Initialize base class with all configuration
        super().__init__(
            host=host,
            port=port,
            database=database,
            token=token,
            container_name=container_name,
            auto_start=auto_start
        )
    
    def write_candle_data(self, ticker: str, period_type: str, period: int,
                          frequency_type: str, frequency: int, 
                          candles: List[Dict[str, Any]]) -> bool:
        """
        Write candle (OHLCV) data for a ticker to InfluxDB.
        
        Arguments:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            period_type: Period type ('day', 'month', 'year', 'ytd')
            period: Number of periods
            frequency_type: Frequency type ('minute', 'daily', 'weekly', 'monthly')
            frequency: Frequency interval
            candles: List of candle dictionaries from Schwab API
            
        Returns:
            True if write successful, False otherwise
        """
        try:
            self.logger.debug(f"Writing {len(candles)} candles for {ticker}")
            
            points = []
            for candle in candles:
                # Extract timestamp
                timestamp_ms = candle.get('datetime')
                if not timestamp_ms:
                    self.logger.warning(f"Candle missing timestamp, skipping")
                    continue
                
                # Convert milliseconds to datetime
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)
                
                # Create point with ticker as measurement
                point = Point("market_data")
                
                # Add tags for filtering (indexed)
                point = point.tag("ticker", ticker)
                point = point.tag("period_type", period_type)
                point = point.tag("period", str(period))
                point = point.tag("frequency_type", frequency_type)
                point = point.tag("frequency", str(frequency))
                
                # Add OHLCV fields
                point = point.field("open", float(candle.get('open', 0)))
                point = point.field("high", float(candle.get('high', 0)))
                point = point.field("low", float(candle.get('low', 0)))
                point = point.field("close", float(candle.get('close', 0)))
                point = point.field("volume", int(candle.get('volume', 0)))
                
                # Set timestamp
                point = point.time(timestamp)
                
                points.append(point)
            
            # Write all points in a single batch
            if points:
                result = self.write_points(points)
                if result:
                    self.logger.info(f"Successfully wrote {len(points)} candles for {ticker} "
                                   f"(period={period}{period_type}, freq={frequency}{frequency_type})")
                return result
            else:
                self.logger.warning(f"No valid candles to write for {ticker}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error writing candle data for {ticker}: {e}")
            return False
    
    def query_candles(self, ticker: str, period_type: Optional[str] = None,
                     period: Optional[int] = None, frequency_type: Optional[str] = None,
                     frequency: Optional[int] = None, 
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None) -> Optional[Any]:
        """
        Query candle data from InfluxDB with optional filters.
        
        Arguments:
            ticker: Stock ticker symbol (required)
            period_type: Optional period type filter
            period: Optional period filter
            frequency_type: Optional frequency type filter
            frequency: Optional frequency filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            Query results as pandas DataFrame if successful, None otherwise
        """
        try:
            # Build SQL query
            sql_parts = [
                "SELECT time, ticker, period_type, period, frequency_type, frequency,",
                "       open, high, low, close, volume",
                f"FROM market_data",
                f"WHERE ticker = '{ticker}'"
            ]
            
            # Add optional filters
            if period_type:
                sql_parts.append(f"AND period_type = '{period_type}'")
            if period is not None:
                sql_parts.append(f"AND period = '{period}'")
            if frequency_type:
                sql_parts.append(f"AND frequency_type = '{frequency_type}'")
            if frequency is not None:
                sql_parts.append(f"AND frequency = '{frequency}'")
            if start_time:
                sql_parts.append(f"AND time >= '{start_time.isoformat()}'")
            if end_time:
                sql_parts.append(f"AND time <= '{end_time.isoformat()}'")
            
            sql_parts.append("ORDER BY time DESC")
            
            sql = " ".join(sql_parts)
            self.logger.debug(f"Querying candles for {ticker}")
            
            return self.query(sql)
            
        except Exception as e:
            self.logger.error(f"Error querying candles for {ticker}: {e}")
            return None
    
    def get_available_tickers(self) -> Optional[List[str]]:
        """
        Get list of all tickers in the database.
        
        Returns:
            List of ticker symbols if successful, None otherwise
        """
        try:
            sql = "SELECT DISTINCT ticker FROM market_data"
            result = self.query(sql)
            
            if result is not None and not result.empty:
                tickers = result['ticker'].unique().tolist()
                self.logger.debug(f"Found {len(tickers)} tickers in database")
                return tickers
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting available tickers: {e}")
            return None
    
    @staticmethod
    def print_access_info(host: str):
        """
        Display InfluxDB access information.
        
        Arguments:
            host: The host URL (from client instance, includes env var configuration)
        """
        print("\n" + "="*60)
        print("InfluxDB is running!")
        print("="*60)
        print(f"API URL: http://{host}")
        print("Health endpoint: /health")
        print("Database: algo-trader-database")
        print("="*60 + "\n")
    
    @classmethod
    def cli(cls):
        """
        Command-line interface for InfluxDB container management.
        
        System-specific CLI that uses algo_trader configuration with fallback to
        infrastructure defaults from artificer.env.
        
        Provides start, stop, restart, status, and logs commands.
        Run as: bazel run //system/algo_trader/clients:influxdb
        """
        # Parse command
        command = sys.argv[1] if len(sys.argv) > 1 else "start"
        
        # Show usage if invalid command
        valid_commands = ["start", "stop", "restart", "status", "logs"]
        if command not in valid_commands:
            print(f"Usage: {sys.argv[0]} {{start|stop|restart|status|logs}}")
            print("\nCommands:")
            print("  start   - Start InfluxDB container (default)")
            print("  stop    - Stop InfluxDB container")
            print("  restart - Restart InfluxDB container")
            print("  status  - Show InfluxDB container status")
            print("  logs    - Show InfluxDB logs (follow mode)")
            sys.exit(1)
        
        try:
            # Create client instance with system-specific configuration
            # This reads ALGO_TRADER_INFLUXDB_* vars with fallback to INFLUXDB3_* vars
            # auto_start=False prevents automatic container startup in __init__
            client = cls(auto_start=False)
            
            if command == "start":
                # Start container
                if not client.start_via_compose():
                    sys.exit(1)
                
                # Use instance host (which has system-specific configuration)
                cls.print_access_info(client.host)
            
            elif command == "stop":
                if not client.stop_via_compose():
                    sys.exit(1)
            
            elif command == "restart":
                # Restart container
                if not client.restart_via_compose():
                    sys.exit(1)
                
                cls.print_access_info(client.host)
            
            elif command == "status":
                client.status_via_compose()
            
            elif command == "logs":
                client.logs_via_compose(follow=True)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    # Allow running as: python -m system.algo_trader.clients.influxdb_client
    AlgoTraderInfluxDBClient.cli()


