import os
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import timedelta

from system.algo_trader.influx.historical_influx_handler import HistoricalInfluxHandler


class TestHistoricalInfluxHandlerUnit:
    @pytest.fixture
    def mock_env_vars(self):
        with patch.dict(os.environ, {
            "INFLUXDB3_AUTH_TOKEN": "test_token",
            "INFLUXDB3_HTTP_BIND_ADDR": "test-url:test-port",
        }):
            yield

    @pytest.fixture
    def mock_dependencies(self, mock_env_vars):
        with patch("infrastructure.clients.influx_client.get_logger") as mock_base_logger, \
             patch("system.algo_trader.influx.historical_influx_handler.get_logger") as mock_handler_logger, \
             patch("infrastructure.clients.influx_client.InfluxDBClient3") as mock_client_class, \
             patch("infrastructure.clients.influx_client.write_client_options") as mock_wco, \
             patch("infrastructure.clients.influx_client.BaseInfluxDBClient.ping") as mock_ping, \
             patch("infrastructure.clients.influx_client.BaseInfluxDBClient._start_server") as mock_start_server:

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_base_logger_instance = MagicMock()
            mock_base_logger.return_value = mock_base_logger_instance

            mock_handler_logger_instance = MagicMock()
            mock_handler_logger.return_value = mock_handler_logger_instance

            mock_ping.return_value = True
            mock_start_server.return_value = True

            yield {
                "base_logger": mock_base_logger,
                "base_logger_instance": mock_base_logger_instance,
                "handler_logger": mock_handler_logger,
                "handler_logger_instance": mock_handler_logger_instance,
                "client_class": mock_client_class,
                "client": mock_client,
                "wco": mock_wco,
                "ping": mock_ping,
                "start_server": mock_start_server,
            }

    def test_initialization_sets_database_and_logger(self, mock_dependencies):
        handler = HistoricalInfluxHandler()
        assert handler.database == "historical_market_data"
        mock_dependencies["handler_logger"].assert_called_with("HistoricalInfluxHandler")

    def test_write_historical_data_success(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        data = [
            {"time": pd.Timestamp("2024-01-01T00:00:00Z"), "open": 100.0, "ticker": "AAPL"}
        ]
        tags = ["ticker"]

        with patch.object(HistoricalInfluxHandler, "write_batch", return_value=True) as mock_write_batch:
            result = handler.write_historical_data("AAPL", data, tags)

        assert result is True
        mock_dependencies["handler_logger_instance"].info.assert_any_call("Writing historical data for AAPL")

        assert mock_write_batch.called
        args, kwargs = mock_write_batch.call_args
        df_arg, name_arg, tags_arg = args
        assert isinstance(df_arg, pd.DataFrame)
        assert name_arg == "AAPL"
        assert tags_arg == tags
        assert set(["time", "open", "ticker"]).issubset(set(df_arg.columns))

    def test_write_historical_data_failure_logs_error(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        data = [
            {"time": pd.Timestamp("2024-01-01T00:00:00Z"), "open": 100.0, "ticker": "AAPL"}
        ]
        tags = ["ticker"]

        with patch.object(HistoricalInfluxHandler, "write_batch", return_value=False):
            result = handler.write_historical_data("AAPL", data, tags)

        assert result is False
        mock_dependencies["handler_logger_instance"].error.assert_any_call(
            "Failed to write historical data for AAPL"
        )

    def test_query_ticker_single_ticker(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        expected_query = "SELECT * FROM AAPL WHERE 1=1"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker("AAPL")

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_multiple_tickers(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        expected_query = "SELECT * FROM AAPL WHERE 1=1"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker(["AAPL", "GOOG", "MSFT"])

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_with_tags(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        expected_query = "SELECT * FROM AAPL WHERE stock IS NOT NULL AND period IS NOT NULL AND frequency IS NOT NULL"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker("AAPL", tags=["stock", "period", "frequency"])

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_with_period_filter(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        expected_query = "SELECT * FROM AAPL WHERE period = '30d'"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker("AAPL", period="30d")

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_with_frequency_filter(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        expected_query = "SELECT * FROM AAPL WHERE frequency = '1m'"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker("AAPL", frequency="1m")

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_with_combined_filters(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        # Mock pd.Timestamp.now to return a fixed time for consistent testing
        fixed_time = pd.Timestamp("2024-10-04T10:30:00+00:00")
        expected_query = f"SELECT * FROM AAPL WHERE stock IS NOT NULL AND time >= '2024-09-04T10:30:00+00:00' AND time <= '{fixed_time.isoformat()}' AND period = '30d' AND frequency = '1m'"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data, \
             patch("pandas.Timestamp.now", return_value=fixed_time):
            result = handler.query_ticker("AAPL", tags=["stock"], period="30d", frequency="1m")

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_no_additional_filters(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        expected_query = "SELECT * FROM AAPL WHERE 1=1"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker("AAPL")

        assert isinstance(result, pd.DataFrame)
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_with_period_and_frequency(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        # Mock pd.Timestamp.now to return a fixed time for consistent testing
        fixed_time = pd.Timestamp("2024-10-04T10:30:00+00:00")
        expected_query = f"SELECT * FROM AAPL WHERE time >= '2024-09-04T10:30:00+00:00' AND time <= '{fixed_time.isoformat()}' AND period = '30d' AND frequency = '1d'"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data, \
             patch("pandas.Timestamp.now", return_value=fixed_time):
            result = handler.query_ticker("AAPL", period="30d", frequency="1d")

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_with_date_range(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        start_date = pd.Timestamp("2024-01-01T00:00:00Z")
        end_date = pd.Timestamp("2024-01-31T23:59:59Z")
        expected_query = "SELECT * FROM AAPL WHERE time >= '2024-01-01T00:00:00+00:00' AND time <= '2024-01-31T23:59:59+00:00'"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker("AAPL", start_date=start_date, end_date=end_date)

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_with_frequency_and_date_range(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        start_date = pd.Timestamp("2024-01-01T00:00:00Z")
        fixed_time = pd.Timestamp("2024-10-04T10:30:00+00:00")
        expected_query = f"SELECT * FROM AAPL WHERE time >= '{start_date.isoformat()}' AND time <= '{fixed_time.isoformat()}' AND frequency = '5m'"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data, \
             patch("pandas.Timestamp.now", return_value=fixed_time):
            result = handler.query_ticker("AAPL", frequency="5m", start_date=start_date)

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_with_string_dates(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        # Use timestamps that will be parsed correctly
        start_ts = pd.Timestamp("2024-01-01T00:00:00+00:00")
        end_ts = pd.Timestamp("2024-01-31T23:59:59+00:00")
        expected_query = f"SELECT * FROM AAPL WHERE time >= '{start_ts.isoformat()}' AND time <= '{end_ts.isoformat()}'"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker("AAPL", start_date="2024-01-01T00:00:00+00:00", end_date="2024-01-31T23:59:59+00:00")

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)

    def test_query_ticker_date_range_swapped(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        # Start date after end date should be swapped
        start_date = pd.Timestamp("2024-01-31T23:59:59Z")
        end_date = pd.Timestamp("2024-01-01T00:00:00Z")
        expected_query = "SELECT * FROM AAPL WHERE time >= '2024-01-01T00:00:00+00:00' AND time <= '2024-01-31T23:59:59+00:00'"

        with patch.object(HistoricalInfluxHandler, "query_data", return_value=pd.DataFrame()) as mock_query_data:
            result = handler.query_ticker("AAPL", start_date=start_date, end_date=end_date)

        assert result is not None
        mock_query_data.assert_called_once_with(expected_query)


    def test_write_historical_data_5m_over_30d_intervals_utc(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        end = pd.Timestamp.now(tz="UTC").floor("5min")
        periods = 30 * 24 * 12  # 5m bars over 30 days
        times = pd.date_range(end=end, periods=periods, freq="5min", tz="UTC")

        ticker = "AAPL"
        period = "30d"
        frequency = "5m"

        data = []
        for i, ts in enumerate(times):
            base = 100.0 + (i * 0.01)
            data.append({
                "time": ts,
                "open": round(base, 2),
                "high": round(base + 1.0, 2),
                "low": round(base - 1.0, 2),
                "close": round(base + 0.5, 2),
                "volume": 100000 + i,
                "ticker": ticker,
                "period": period,
                "frequency": frequency,
            })

        tags = ["stock", "period", "frequency"]

        with patch.object(HistoricalInfluxHandler, "write_batch", return_value=True) as mock_write_batch:
            result = handler.write_historical_data(ticker, data, tags)

        assert result is True
        args, kwargs = mock_write_batch.call_args
        df_arg, name_arg, tags_arg = args

        assert name_arg == ticker
        assert tags_arg == tags
        assert len(df_arg) == periods
        assert str(df_arg["time"].dtype) == "datetime64[ns, UTC]"
        assert df_arg["time"].is_monotonic_increasing
        diffs = df_arg["time"].diff().dropna()
        assert len(diffs) > 0 and all(diffs == pd.Timedelta(minutes=5))
        assert set(df_arg["period"].unique()) == {period}
        assert set(df_arg["frequency"].unique()) == {frequency}


    def test_write_historical_data_1d_over_1y_intervals_utc(self, mock_dependencies):
        handler = HistoricalInfluxHandler()

        end = pd.Timestamp.now(tz="UTC").floor("D")
        periods = 365  # 1y (non-leap) daily bars
        times = pd.date_range(end=end, periods=periods, freq="1D", tz="UTC")

        ticker = "SPY"
        period = "1y"
        frequency = "1d"

        data = []
        for i, ts in enumerate(times):
            base = 400.0 + (i * 0.1)
            data.append({
                "time": ts,
                "open": round(base, 2),
                "high": round(base + 2.0, 2),
                "low": round(base - 2.0, 2),
                "close": round(base + 0.8, 2),
                "volume": 1000000 + (i * 1000),
                "ticker": ticker,
                "period": period,
                "frequency": frequency,
            })

        tags = ["stock", "period", "frequency"]

        with patch.object(HistoricalInfluxHandler, "write_batch", return_value=True) as mock_write_batch:
            result = handler.write_historical_data(ticker, data, tags)

        assert result is True
        args, kwargs = mock_write_batch.call_args
        df_arg, name_arg, tags_arg = args

        assert name_arg == ticker
        assert tags_arg == tags
        assert len(df_arg) == periods
        assert str(df_arg["time"].dtype) == "datetime64[ns, UTC]"
        assert df_arg["time"].is_monotonic_increasing
        diffs = df_arg["time"].diff().dropna()
        assert len(diffs) > 0 and all(diffs == pd.Timedelta(days=1))
        assert set(df_arg["period"].unique()) == {period}
        assert set(df_arg["frequency"].unique()) == {frequency}

class TestHistoricalInfluxHandlerIntegration:
    """Integration tests for HistoricalInfluxHandler (requires local InfluxDB running)"""

    @pytest.fixture(scope="session")
    def influx_client(self):
        """Create client connected to local InfluxDB"""
        client = HistoricalInfluxHandler( database="historical_market_test")
        return client

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Generate sample OHLCV data for a single ticker"""
        def _generate_data(ticker="AAPL", start_time=None, num_points=5, interval_minutes=1, period="30d", frequency="1m"):
            # Build UTC-aware timestamps using date_range
            if start_time is None:
                end = pd.Timestamp.now(tz="UTC").floor(f"{interval_minutes}min")
                times = pd.date_range(end=end, periods=num_points, freq=f"{interval_minutes}min", tz="UTC")
            else:
                start = pd.Timestamp(start_time, tz="UTC") if pd.Timestamp(start_time).tz is None else pd.Timestamp(start_time)
                times = pd.date_range(start=start, periods=num_points, freq=f"{interval_minutes}min", tz="UTC")

            data = []
            for i, ts in enumerate(times):
                base_price = 150.0 + (i * 2.0)
                spread = 2.0
                volume_base = 1000000

                data.append({
                    "time": ts,
                    "open": round(base_price + (i * 0.1), 2),
                    "high": round(base_price + spread + (i * 0.1), 2),
                    "low": round(base_price - spread + (i * 0.1), 2),
                    "close": round(base_price + 1.0 + (i * 0.1), 2),
                    "volume": int(volume_base + (i * 100000)),
                    "ticker": ticker,
                    "period": period,
                    "frequency": frequency
                })

            return data
        return _generate_data

    @pytest.fixture
    def multi_ticker_data(self):
        """Generate sample OHLCV data for multiple tickers"""
        def _generate_multi_ticker_data(tickers=None, start_time=None, num_points=3, interval_minutes=1, period="30d", frequency="1m"):
            if tickers is None:
                tickers = ["AAPL", "GOOG", "MSFT"]
            # Build base UTC-aware timeline
            if start_time is None:
                end = pd.Timestamp.now(tz="UTC").floor(f"{interval_minutes}min")
                base_times = pd.date_range(end=end, periods=num_points, freq=f"{interval_minutes}min", tz="UTC")
            else:
                start = pd.Timestamp(start_time, tz="UTC") if pd.Timestamp(start_time).tz is None else pd.Timestamp(start_time)
                base_times = pd.date_range(start=start, periods=num_points, freq=f"{interval_minutes}min", tz="UTC")

            all_data = []
            for ticker in tickers:
                base_prices = {"AAPL": 150.0, "GOOG": 2800.0, "MSFT": 380.0}
                start_price = base_prices.get(ticker, 100.0)
                for i, ts in enumerate(base_times):
                    all_data.append({
                        "time": ts,
                        "open": round(start_price + (i * 0.5), 2),
                        "high": round(start_price + 2.0 + (i * 0.5), 2),
                        "low": round(start_price - 1.5 + (i * 0.5), 2),
                        "close": round(start_price + 1.2 + (i * 0.5), 2),
                        "volume": int(1000000 + (i * 50000)),
                        "ticker": ticker,
                        "period": period,
                        "frequency": frequency
                    })

            return all_data
        return _generate_multi_ticker_data

    @pytest.fixture
    def historical_time_series(self):
        """Generate historical time series data with different date ranges"""
        def _generate_historical_data(ticker="AAPL", days_back=30, num_points=10, period=None, frequency="1d"):
            end = pd.Timestamp.now(tz="UTC").floor("D")
            start = end - pd.Timedelta(days=days_back)

            # Default period based on days_back if not provided
            if period is None:
                period = f"{days_back}d"

            # Build UTC-aware date_range based on frequency
            if frequency.lower() in {"1d", "1day", "d", "day"}:
                times = pd.date_range(start=start, end=end, periods=num_points, tz="UTC")
            else:
                # Fallback: infer from frequency string if it ends with 'm' for minutes
                if frequency.endswith("m"):
                    minutes = int(frequency[:-1])
                    times = pd.date_range(end=end, periods=num_points, freq=f"{minutes}min", tz="UTC")
                else:
                    # Default to daily spacing
                    times = pd.date_range(start=start, end=end, periods=num_points, tz="UTC")

            data = []
            for i, ts in enumerate(times):
                data.append({
                    "time": ts,
                    "open": round(150.0 + (i * 0.2), 2),
                    "high": round(152.0 + (i * 0.2), 2),
                    "low": round(148.0 + (i * 0.2), 2),
                    "close": round(151.0 + (i * 0.2), 2),
                    "volume": int(1000000 + (i * 10000)),
                    "ticker": ticker,
                    "period": period,
                    "frequency": frequency
                })

            return data
        return _generate_historical_data



    def test_client_initialization(self, influx_client):
        assert influx_client.database == "historical_market_test"

    def test_batch_write_ohlcv(self, influx_client, sample_ohlcv_data):
        ticker = "AAPL"
        data = sample_ohlcv_data(ticker=ticker, num_points=3, interval_minutes=1, period="30d", frequency="1m")
        tags = ["stock", "period", "frequency"]
        assert influx_client.write_historical_data(ticker, data, tags) is True

    def test_batch_write_multiple_tickers(self, influx_client, multi_ticker_data):
        tickers = ["AAPL", "GOOG", "MSFT"]
        data = multi_ticker_data(tickers=tickers, num_points=2, interval_minutes=1, period="30d", frequency="1m")
        tags = ["stock", "period", "frequency"]
        assert influx_client.write_historical_data(tickers, data, tags) is True

    def test_batch_write_custom_ticker_data(self, influx_client, sample_ohlcv_data):
        """Test with custom ticker and different parameters"""
        ticker = "TSLA"
        data = sample_ohlcv_data(ticker=ticker, num_points=10, interval_minutes=5, period="5m", frequency="5m")
        tags = ["stock", "period", "frequency"]
        assert influx_client.write_historical_data(ticker, data, tags) is True

    def test_batch_write_historical_range(self, influx_client, historical_time_series):
        """Test with historical date range data"""
        ticker = "NVDA"
        data = historical_time_series(ticker=ticker, days_back=60, num_points=20, period="60d", frequency="1d")
        tags = ["stock", "period", "frequency"]
        assert influx_client.write_historical_data(ticker, data, tags) is True

    
