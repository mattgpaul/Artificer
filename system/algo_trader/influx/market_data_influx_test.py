import time
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta, timezone

from system.algo_trader.influx.market_data_influx import MarketDataInflux
from infrastructure.clients.influx_client import BatchWriteConfig

class TestMarketDataInflux:
    """Integration tests for MarketDataInflux (requires local InfluxDB running)"""

    @pytest.fixture(scope="session")
    def influx_client(self):
        """Create client connected to local InfluxDB with test-optimized batch settings"""
        # Create test-optimized batch configuration
        test_config = BatchWriteConfig(
            batch_size=10,  
            flush_interval=500,  
            jitter_interval=2_000,
            retry_interval=5_000,
            max_retries=5,
            max_retry_delay=30_000,
            exponential_base=2
        )
        
        # Pass config during instantiation
        client = MarketDataInflux(
            database="historical_market_test", 
            write_config=test_config
        )
        
        yield client
        
        # No cleanup needed - write method now handles completion

    @pytest.fixture(scope="session")
    def tickers(self):
        return ["AAPL", "GOOG", "MSFT"]

    @pytest.fixture(scope="session")
    def test_data_intraday(self, tickers):
        # Intraday: 5-minute intervals for today
        base_time = datetime.now(timezone.utc).replace(second=0, microsecond=0, minute=0, hour=14)
        data = []
        for ticker in tickers:
            candles = []
            for i in range(5):  # 5 intervals
                ts = base_time + timedelta(minutes=5 * i)
                candles.append({
                    "open": 100 + i + hash(ticker) % 10,
                    "high": 101 + i + hash(ticker) % 10,
                    "low": 99 + i + hash(ticker) % 10,
                    "close": 100.5 + i + hash(ticker) % 10,
                    "volume": 1000 + i * 10 + hash(ticker) % 100,
                    "datetime": int(ts.timestamp() * 1000)
                })
            data.append({
                "symbol": ticker,
                "empty": False,
                "previousClose": 100 + hash(ticker) % 10,
                "previousCloseDate": int((base_time - timedelta(days=1)).timestamp() * 1000),
                "candles": candles
            })
        return data

    @pytest.fixture(scope="session")
    def test_data_daily(self, tickers):
        # Daily: 5 days, one row per day per ticker
        base_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        data = []
        for ticker in tickers:
            candles = []
            for i in range(5):
                ts = base_date - timedelta(days=4 - i)
                candles.append({
                    "open": 200 + i + hash(ticker) % 10,
                    "high": 201 + i + hash(ticker) % 10,
                    "low": 199 + i + hash(ticker) % 10,
                    "close": 200.5 + i + hash(ticker) % 10,
                    "volume": 2000 + i * 10 + hash(ticker) % 100,
                    "datetime": int(ts.timestamp() * 1000)
                })
            data.append({
                "symbol": ticker,
                "empty": False,
                "previousClose": 200 + hash(ticker) % 10,
                "previousCloseDate": int((base_date - timedelta(days=5)).timestamp() * 1000),
                "candles": candles
            })
        return data

    def test_influx_server_up(self, influx_client):
        ping = influx_client.ping()
        assert ping

    def test_does_database_exist(self, influx_client):
        database = influx_client._check_database()
        assert database

    def test_write_data(self, influx_client, test_data_intraday, test_data_daily):
        # Write options already set at instantiation
        for ticker_data in test_data_intraday:
            success = influx_client.write(
                data=ticker_data["candles"],
                ticker=ticker_data["symbol"],
                table="stock",
            )
            time.sleep(1)
            assert success

        for ticker_data in test_data_daily:
            success = influx_client.write(
                data=ticker_data["candles"],
                ticker=ticker_data["symbol"],
                table="stock",
            )
            time.sleep(1)
            assert success

    def test_query_data(self, influx_client):
        # Test query tag columns, no time range
        query = '''SHOW COLUMNS FROM stock'''
        df = influx_client.query(query=query)
        # stock should have these columns, based on our write
        for col in ["open", "high", "low", "close", "volume", "ticker"]:
            influx_client.logger.debug(f"{df['column_name']}")
            assert col in df["column_name"].tolist()

    def test_query_ticker(self, influx_client, tickers):
        for symbol in tickers:
            query = f""" 
            SELECT * FROM stock WHERE ticker = '{symbol}'
            """
            df = influx_client.query(query)
            influx_client.logger.debug(f"{df.shape}")
            assert df.shape == (6, 7)

    def test_query_time_range(self, influx_client, tickers, test_data_intraday, test_data_daily):
        # Use dynamic time range based on the test data timestamps
        # Get the earliest and latest timestamps from the test data
        all_times = []
        
        # Collect all timestamps from intraday data
        for ticker_data in test_data_intraday:
            for candle in ticker_data["candles"]:
                all_times.append(candle["datetime"])
        
        # Collect all timestamps from daily data  
        for ticker_data in test_data_daily:
            for candle in ticker_data["candles"]:
                all_times.append(candle["datetime"])
        
        # Convert to pandas timestamps and find range (timezone-naive to match InfluxDB)
        timestamps = [pd.Timestamp(dt, unit='ms') for dt in all_times]  # No timezone
        start_time = min(timestamps) - pd.Timedelta(minutes=1)  # Add small buffer
        end_time = max(timestamps) + pd.Timedelta(minutes=1)    # Add small buffer

        for symbol in tickers:
            query = (
                f"SELECT * FROM stock WHERE ticker = '{symbol}' "
                f"AND time >= '{start_time}' AND time <= '{end_time}'"
            )
            df = influx_client.query(query)
            influx_client.logger.debug(f"Queried {symbol} rows: {df.shape[0]}")
            # All returned times should be within the range
            influx_client.logger.debug(f"{df['time']}")
            assert not df.empty
            
            # Both sides are now timezone-naive, so direct comparison works
            assert df['time'].min() >= start_time
            assert df['time'].max() <= end_time
    
