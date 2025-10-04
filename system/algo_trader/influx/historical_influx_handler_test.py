import os
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

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


class TestHistoricalInfluxHandlerIntegration:
    """Integration tests for HistoricalInfluxHandler (requires local InfluxDB running)"""

    @pytest.fixture(scope="session")
    def influx_client(self):
        """Create client connected to local InfluxDB"""        
        client = HistoricalInfluxHandler( database="historical_market_test")
        return client

    def test_client_initialization(self, influx_client):
        assert influx_client.database == "historical_market_test"

    def test_batch_write_ohlcv(self, influx_client):
        ticker = "AAPL"
        now = pd.Timestamp.utcnow().floor("s")
        data = [
            {"time": now, "open": 150.0, "high": 152.0, "low": 149.5, "close": 151.0, "volume": 1000000, "ticker": ticker},
            {"time": now + pd.Timedelta(minutes=1), "open": 151.0, "high": 153.0, "low": 150.5, "close": 152.5, "volume": 1100000, "ticker": ticker},
        ]
        tags = ["ticker"]
        assert influx_client.write_historical_data(ticker, data, tags) is True
