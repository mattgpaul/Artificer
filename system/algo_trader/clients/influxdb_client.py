"""Algo-trader InfluxDB client.

This module provides a system-specific wrapper around the infrastructure InfluxDB
client, with helpers for writing and querying candle (OHLCV) market data.
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from influxdb_client_3 import Point

from infrastructure.clients.influxdb_client import BaseInfluxDBClient


@dataclass(frozen=True)
class CandleSeriesSpec:
    """Identifies a market-data candle series by period/frequency settings."""

    period_type: str
    period: int
    frequency_type: str
    frequency: int


@dataclass(frozen=True)
class CandleQueryFilters:
    """Optional filters for querying candle data."""

    spec: CandleSeriesSpec | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class AlgoTraderInfluxDBClient(BaseInfluxDBClient):
    """InfluxDB client for the algo_trader system.

    Handles storage of historical market data organized by ticker symbol.
    Data is tagged with ticker, period, and frequency for flexible querying.
    """

    def __init__(self, auto_start: bool = False):
        """Initialize AlgoTrader InfluxDB client.

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
        host_with_port = os.getenv(
            "ALGO_TRADER_INFLUXDB_HOST", os.getenv("INFLUXDB3_HTTP_BIND_ADDR", "localhost:8181")
        )

        # Parse host and port
        if ":" in host_with_port:
            host, port_str = host_with_port.rsplit(":", 1)
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
            auto_start=auto_start,
        )

    def write_candle_data(
        self, ticker: str, *, spec: CandleSeriesSpec, candles: list[dict[str, Any]]
    ) -> bool:
        """Write candle (OHLCV) data for a ticker to InfluxDB.

        Arguments:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            spec: Candle series identifier (period/frequency settings)
            candles: List of candle dictionaries from Schwab API

        Returns:
            True if write successful, False otherwise
        """
        try:
            self.logger.debug(f"Writing {len(candles)} candles for {ticker}")

            period_type = spec.period_type
            period = spec.period
            frequency_type = spec.frequency_type
            frequency = spec.frequency

            points = []
            for candle in candles:
                # Extract timestamp
                timestamp_ms = candle.get("datetime")
                if not timestamp_ms:
                    self.logger.warning("Candle missing timestamp, skipping")
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
                point = point.field("open", float(candle.get("open", 0)))
                point = point.field("high", float(candle.get("high", 0)))
                point = point.field("low", float(candle.get("low", 0)))
                point = point.field("close", float(candle.get("close", 0)))
                point = point.field("volume", int(candle.get("volume", 0)))

                # Set timestamp
                point = point.time(timestamp)

                points.append(point)

            # Write all points in a single batch
            if points:
                result = self.write_points(points)
                if result:
                    self.logger.info(
                        f"Successfully wrote {len(points)} candles for {ticker} "
                        f"(period={period}{period_type}, freq={frequency}{frequency_type})"
                    )
                return result
            else:
                self.logger.warning(f"No valid candles to write for {ticker}")
                return False

        except Exception as e:
            self.logger.error(f"Error writing candle data for {ticker}: {e}")
            return False

    def query_candles(
        self, ticker: str, *, filters: CandleQueryFilters | None = None
    ) -> Any | None:
        """Query candle data from InfluxDB with optional filters.

        Arguments:
            ticker: Stock ticker symbol (required)
            filters: Optional query filters (series + time bounds)

        Returns:
            Query results as pandas DataFrame if successful, None otherwise
        """
        try:
            if filters is None:
                filters = CandleQueryFilters()

            # Build SQL query
            sql_parts = [
                "SELECT time, ticker, period_type, period, frequency_type, frequency,",
                "       open, high, low, close, volume",
                "FROM market_data",
                f"WHERE ticker = '{ticker}'",
            ]

            # Add optional filters
            if filters.spec is not None:
                sql_parts.append(f"AND period_type = '{filters.spec.period_type}'")
                sql_parts.append(f"AND period = '{filters.spec.period}'")
                sql_parts.append(f"AND frequency_type = '{filters.spec.frequency_type}'")
                sql_parts.append(f"AND frequency = '{filters.spec.frequency}'")
            if filters.start_time:
                sql_parts.append(f"AND time >= '{filters.start_time.isoformat()}'")
            if filters.end_time:
                sql_parts.append(f"AND time <= '{filters.end_time.isoformat()}'")

            sql_parts.append("ORDER BY time DESC")

            sql = " ".join(sql_parts)
            self.logger.debug(f"Querying candles for {ticker}")

            return self.query(sql)

        except Exception as e:
            self.logger.error(f"Error querying candles for {ticker}: {e}")
            return None

    def get_available_tickers(self) -> list[str] | None:
        """Get list of all tickers in the database.

        Returns:
            List of ticker symbols if successful, None otherwise
        """
        try:
            sql = "SELECT DISTINCT ticker FROM market_data"
            result = self.query(sql)

            if result is not None and not result.empty:
                tickers = result["ticker"].unique().tolist()
                self.logger.debug(f"Found {len(tickers)} tickers in database")
                return tickers
            else:
                return []

        except Exception as e:
            self.logger.error(f"Error getting available tickers: {e}")
            return None

    @staticmethod
    def print_access_info(host: str):
        """Display InfluxDB access information.

        Arguments:
            host: The host URL (from client instance, includes env var configuration)
        """
        print("\n" + "=" * 60)
        print("InfluxDB is running!")
        print("=" * 60)
        print(f"API URL: http://{host}")
        print("Health endpoint: /health")
        print("Database: algo-trader-database")
        print("=" * 60 + "\n")

    @classmethod
    def cli(cls):
        """Command-line interface for InfluxDB container management.

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
