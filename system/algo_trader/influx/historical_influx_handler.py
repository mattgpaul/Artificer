import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Union, List

from infrastructure.clients.influx_client import BaseInfluxDBClient

from infrastructure.logging.logger import get_logger

class HistoricalInfluxHandler(BaseInfluxDBClient):
    def __init__(self, database: str = "historical_market_data"):
        super().__init__(database=database)
        self.logger = get_logger(self.__class__.__name__)

    def write_historical_data(self, ticker: str | list[str], data: list[dict], tags: list[str]) -> bool:
        self.logger.info(f"Writing historical data for {ticker}")
        data = pd.DataFrame(data)
        success = self.write_batch(data, ticker, tags)
        if not success:
            self.logger.error(f"Failed to write historical data for {ticker}")
        return success

    def query_ticker(self, ticker: Union[str, List[str]], tags: Optional[List[str]] = None, period: Optional[str] = None, frequency: Optional[str] = None, start_date: Optional[Union[str, pd.Timestamp]] = None, end_date: Optional[Union[str, pd.Timestamp]] = None) -> pd.DataFrame:
        """
        Query historical ticker data with flexible time-based filtering options.

        Args:
            ticker: Single ticker symbol or list of ticker symbols
            tags: List of tag names to filter by (e.g., ["stock", "period", "frequency"])
            period: Specific period to filter by (e.g., "30d", "5m", "1y")
            frequency: Specific frequency to filter by (e.g., "1m", "1d", "5m")
            start_date: Start date for the query (can be string or pd.Timestamp)
            end_date: End date for the query (can be string or pd.Timestamp)

        Returns:
            DataFrame with matching historical data
        """
        # Handle ticker parameter (single or multiple)
        if isinstance(ticker, list):
            ticker_list = ticker
            # Use first ticker as measurement name for InfluxDB query
            measurement = ticker[0] if ticker else "measurement"
        else:
            ticker_list = [ticker]
            measurement = ticker

        # Build WHERE clause
        where_conditions = []

        if tags:
            for tag in tags:
                where_conditions.append(f"{tag} IS NOT NULL")

        # Handle time-based filtering
        time_conditions = self._build_time_conditions(period, frequency, start_date, end_date)
        if time_conditions:
            where_conditions.extend(time_conditions)

        # Add period filter if specified (but not when using date ranges)
        if period and not (start_date or end_date):
            where_conditions.append(f"period = '{period}'")

        # Add frequency filter if specified
        if frequency:
            where_conditions.append(f"frequency = '{frequency}'")

        # Construct the full query
        if where_conditions:
            where_clause = " AND ".join(where_conditions)
            query = f"SELECT * FROM {measurement} WHERE {where_clause}"
        else:
            query = f"SELECT * FROM {measurement}"

        self.logger.debug(f"Executing query: {query}")
        return self.query_data(query)

    def _build_time_conditions(self, period: Optional[str], frequency: Optional[str], start_date: Optional[Union[str, pd.Timestamp]], end_date: Optional[Union[str, pd.Timestamp]]) -> List[str]:
        """
        Build time-based WHERE conditions for InfluxDB queries.

        Handles various combinations of period, frequency, and date ranges.
        """
        conditions = []

        # Handle date range parameters
        if start_date or end_date:
            # Convert string dates to timestamps if needed
            start_ts = self._parse_date(start_date) if start_date else None
            end_ts = self._parse_date(end_date) if end_date else pd.Timestamp.now(tz="UTC")

            # Default start time if only end_date is provided
            if not start_ts:
                # If frequency is provided, calculate a reasonable start time
                if frequency:
                    start_ts = self._calculate_default_start_time(end_ts, frequency)
                else:
                    # Default to 30 days back if no frequency is provided
                    start_ts = end_ts - timedelta(days=30)

            # Ensure start is before end
            if start_ts and end_ts and start_ts >= end_ts:
                self.logger.warning(f"Start date {start_ts} is after or equal to end date {end_ts}, swapping them")
                start_ts, end_ts = end_ts, start_ts

            # Format for InfluxDB query (ISO format)
            if start_ts:
                conditions.append(f"time >= '{start_ts.isoformat()}'")
            if end_ts:
                conditions.append(f"time <= '{end_ts.isoformat()}'")

        # Handle period parameter (when no explicit date range is provided)
        elif period and frequency:
            # Calculate time range based on period and frequency
            end_time = pd.Timestamp.now(tz="UTC")
            start_time = self._calculate_period_start_time(end_time, period, frequency)

            if start_time:
                conditions.append(f"time >= '{start_time.isoformat()}'")
                conditions.append(f"time <= '{end_time.isoformat()}'")

        return conditions

    def _parse_date(self, date_input: Union[str, pd.Timestamp]) -> Optional[pd.Timestamp]:
        """Parse various date input formats into a pandas Timestamp."""
        if isinstance(date_input, pd.Timestamp):
            return date_input
        elif isinstance(date_input, str):
            try:
                # Try ISO format first
                return pd.Timestamp(date_input)
            except ValueError:
                try:
                    # Try common formats
                    return pd.Timestamp(date_input)
                except ValueError:
                    self.logger.warning(f"Could not parse date: {date_input}")
                    return None
        return None

    def _calculate_period_start_time(self, end_time: pd.Timestamp, period: str, frequency: str) -> Optional[pd.Timestamp]:
        """Calculate start time based on period and frequency."""
        try:
            # Parse period (e.g., "30d", "5m", "1y")
            if period.endswith('d'):
                days = int(period[:-1])
                return end_time - timedelta(days=days)
            elif period.endswith('m'):
                minutes = int(period[:-1])
                return end_time - timedelta(minutes=minutes)
            elif period.endswith('y'):
                years = int(period[:-1])
                return end_time - timedelta(days=years * 365)  # Approximate
            elif period.endswith('h'):
                hours = int(period[:-1])
                return end_time - timedelta(hours=hours)
            else:
                self.logger.warning(f"Unknown period format: {period}")
                return None
        except ValueError:
            self.logger.warning(f"Could not parse period: {period}")
            return None

    def _calculate_default_start_time(self, end_time: pd.Timestamp, frequency: str) -> pd.Timestamp:
        """Calculate a reasonable default start time based on frequency."""
        try:
            if frequency.endswith('m'):
                minutes = int(frequency[:-1])
                # Default to 24 hours of data for minute frequencies
                return end_time - timedelta(hours=24)
            elif frequency.endswith('h'):
                hours = int(frequency[:-1])
                # Default to 7 days for hourly data
                return end_time - timedelta(days=7)
            elif frequency.endswith('d') or frequency.endswith('D'):
                # Default to 90 days for daily data
                return end_time - timedelta(days=90)
            else:
                # Default fallback
                return end_time - timedelta(days=30)
        except ValueError:
            self.logger.warning(f"Could not parse frequency: {frequency}")
            return end_time - timedelta(days=30)

