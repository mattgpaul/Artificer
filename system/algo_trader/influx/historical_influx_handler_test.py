import os
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta, timezone

from system.algo_trader.influx.historical_influx_handler import HistoricalInfluxHandler

class TestHistoricalInfluxHandler:
    """Integration tests for HistoricalInfluxHandler (requires local InfluxDB running)"""

    @pytest.fixture(scope="session")
    def influx_client(self):
        """Create client connected to local InfluxDB"""
        client = HistoricalInfluxHandler( database="historical_market_test")
        return client

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
            assert success

        for ticker_data in test_data_daily:
            success = influx_client.write(
                data=ticker_data["candles"],
                ticker=ticker_data["symbol"],
                table="stock",
            )
            assert success
    
