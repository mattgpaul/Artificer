"""Unit tests for InfluxPublisher - InfluxDB Publisher Service.

Tests cover initialization, queue processing, database mapping, and signal handling.
All external dependencies are mocked to avoid requiring Redis or InfluxDB servers.
"""

import os
import signal
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from system.algo_trader.influx.publisher.config import (
    BACKTEST_DATABASE,
    FUNDAMENTALS_BATCH_SIZE,
    FUNDAMENTALS_DATABASE,
    OHLCV_BATCH_SIZE,
    OHLCV_DATABASE,
    TRADING_JOURNAL_BATCH_SIZE,
    TRADING_JOURNAL_DATABASE,
)
from system.algo_trader.influx.publisher.publisher import InfluxPublisher, main
from system.algo_trader.influx.publisher.queue_processor import process_queue


class TestInfluxPublisherInitialization:
    """Test InfluxPublisher initialization."""

    def test_initialization_loads_config(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test initialization loads configuration from file."""
        publisher = InfluxPublisher(temp_config_file)

        assert publisher.config is not None
        assert "queues" in publisher.config
        assert len(publisher.config["queues"]) == 2

    def test_initialization_creates_queue_broker(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test initialization creates QueueBroker with namespace."""
        publisher = InfluxPublisher(temp_config_file)

        assert publisher.queue_broker is not None

    def test_initialization_sets_signal_handlers(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test initialization sets up signal handlers."""
        InfluxPublisher(temp_config_file)

        assert mock_signal.call_count == 2
        assert mock_signal.call_args_list[0][0][0] == signal.SIGTERM
        assert mock_signal.call_args_list[1][0][0] == signal.SIGINT

    def test_initialization_maps_ohlcv_queue_to_database(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test OHLCV queue maps to correct database."""
        publisher = InfluxPublisher(temp_config_file)

        assert "ohlcv_queue" in publisher.influx_clients
        # Verify MarketDataInflux was called with correct database
        mock_market_data_influx["class"].assert_called()
        call_args = mock_market_data_influx["class"].call_args_list
        ohlcv_call = next(
            (call for call in call_args if call[1]["database"] == OHLCV_DATABASE), None
        )
        assert ohlcv_call is not None

    def test_initialization_maps_fundamentals_queue_to_database(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test fundamentals queue maps to correct database."""
        publisher = InfluxPublisher(temp_config_file)

        assert "fundamentals_queue" in publisher.influx_clients

    def test_initialization_uses_protected_ohlcv_batch_size(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test OHLCV queue uses protected batch size constant."""
        InfluxPublisher(temp_config_file)

        # Verify MarketDataInflux was called with protected batch size
        mock_market_data_influx["class"].assert_called()
        call_args = mock_market_data_influx["class"].call_args_list
        ohlcv_call = next(
            (call for call in call_args if call[1]["write_config"].batch_size == OHLCV_BATCH_SIZE),
            None,
        )
        assert ohlcv_call is not None

    def test_initialization_uses_fundamentals_batch_size(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test fundamentals queue uses correct batch size."""
        InfluxPublisher(temp_config_file)

        mock_market_data_influx["class"].assert_called()
        call_args = mock_market_data_influx["class"].call_args_list
        fundamentals_call = next(
            (
                call
                for call in call_args
                if call[1]["write_config"].batch_size == FUNDAMENTALS_BATCH_SIZE
            ),
            None,
        )
        assert fundamentals_call is not None

    def test_initialization_with_missing_config_file(
        self, mock_publisher_logger, mock_queue_broker, mock_market_data_influx, mock_signal
    ):
        """Test initialization exits on missing config file."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(SystemExit):
                InfluxPublisher("/nonexistent/config.yaml")

    def test_initialization_with_invalid_queue_name(
        self, mock_publisher_logger, mock_queue_broker, mock_market_data_influx, mock_signal
    ):
        """Test initialization exits on unknown queue name."""
        invalid_config = {"queues": [{"name": "unknown_queue", "table": "test"}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name

        try:
            with pytest.raises(SystemExit):
                InfluxPublisher(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_initialization_uses_config_params(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test initialization uses config parameters for write config."""
        InfluxPublisher(temp_config_file)

        mock_market_data_influx["class"].assert_called()
        call_args = mock_market_data_influx["class"].call_args_list[0]
        write_config = call_args[1]["write_config"]

        assert write_config.flush_interval == 5000
        assert write_config.jitter_interval == 1000
        assert write_config.retry_interval == 10000
        assert write_config.max_retries == 3
        assert write_config.max_retry_delay == 30000
        assert write_config.exponential_base == 2


class TestInfluxPublisherQueueProcessing:
    """Test queue processing operations."""

    @pytest.fixture
    def publisher(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Create publisher instance for testing."""
        return InfluxPublisher(temp_config_file)

    def test_process_queue_skips_empty_queue(self, publisher, mock_queue_broker):
        """Test processing skips empty queues."""
        mock_queue_broker.get_queue_size.return_value = 0

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        mock_queue_broker.dequeue.assert_not_called()

    def test_process_queue_processes_items(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing dequeues and writes items."""
        mock_queue_broker.get_queue_size.return_value = 2
        mock_queue_broker.dequeue.side_effect = ["item1", "item2", None]
        mock_queue_broker.get_data.side_effect = [
            {"ticker": "AAPL", "candles": [{"datetime": [1609459200000], "close": [104.0]}]},
            {"ticker": "TSLA", "candles": [{"datetime": [1609459200000], "close": [300.0]}]},
        ]
        mock_market_data_influx["instance"].write.return_value = True
        publisher.influx_clients[
            "ohlcv_queue"
        ].database = "ohlcv"  # Set database to avoid new client creation

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        assert mock_queue_broker.dequeue.call_count >= 2
        assert mock_market_data_influx["instance"].write.call_count == 2

    def test_process_queue_handles_missing_data(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing handles missing data gracefully."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = None

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        mock_queue_broker.delete_data.assert_not_called()
        mock_market_data_influx["instance"].write.assert_not_called()

    def test_process_queue_handles_invalid_data_structure(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing handles invalid data structure."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = {"invalid": "data"}  # Missing ticker and candles

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        mock_queue_broker.delete_data.assert_called_once_with("ohlcv_queue", "item1")
        mock_market_data_influx["instance"].write.assert_not_called()

    def test_process_queue_handles_write_failure(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing handles write failures."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "candles": [{"datetime": [1609459200000], "close": [104.0]}],
        }
        mock_market_data_influx["instance"].write_sync.return_value = False

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        mock_queue_broker.delete_data.assert_called_once_with("ohlcv_queue", "item1")

    def test_process_queue_handles_write_exception(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing handles write exceptions."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "candles": [{"datetime": [1609459200000], "close": [104.0]}],
        }
        mock_market_data_influx["instance"].write_sync.side_effect = Exception("Write error")

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        mock_queue_broker.delete_data.assert_called_once_with("ohlcv_queue", "item1")

    def test_process_queue_supports_candles_format(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing supports candles data format."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "candles": [{"datetime": [1609459200000], "close": [104.0]}],
        }
        mock_market_data_influx["instance"].write.return_value = True
        publisher.influx_clients[
            "ohlcv_queue"
        ].database = "ohlcv"  # Set database to avoid new client creation

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        mock_market_data_influx["instance"].write.assert_called_once()
        call_args = mock_market_data_influx["instance"].write.call_args
        assert call_args[1]["ticker"] == "AAPL"

    def test_process_queue_supports_data_format(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing supports data format (for fundamentals)."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "data": {"datetime": [1609459200000], "revenue": [1000000]},
        }
        mock_market_data_influx["instance"].write.return_value = True
        publisher.influx_clients[
            "fundamentals_queue"
        ].database = "fundamentals"  # Set database to avoid new client creation

        queue_config = {"name": "fundamentals_queue", "table": "fundamentals"}
        process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["fundamentals_queue"],
            lambda: True,
            publisher.logger,
        )

        mock_market_data_influx["instance"].write.assert_called_once()
        call_args = mock_market_data_influx["instance"].write.call_args
        assert call_args[1]["ticker"] == "AAPL"

    def test_process_queue_handles_empty_candles_list(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing handles empty candles list for ohlcv_queue."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "candles": [],  # Empty list
        }

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        processed, failed = process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        assert processed == 0
        assert failed == 1
        mock_queue_broker.delete_data.assert_called_once_with("ohlcv_queue", "item1")
        mock_market_data_influx["instance"].write.assert_not_called()

    def test_process_queue_handles_empty_datetime_array(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing handles empty datetime array for ohlcv_queue."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "candles": {"datetime": [], "open": [], "close": []},  # Empty datetime array
        }

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        processed, failed = process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["ohlcv_queue"],
            lambda: True,
            publisher.logger,
        )

        assert processed == 0
        assert failed == 1
        mock_queue_broker.delete_data.assert_called_once_with("ohlcv_queue", "item1")
        mock_market_data_influx["instance"].write.assert_not_called()

    def test_process_queue_handles_empty_fundamentals_data(
        self, publisher, mock_queue_broker, mock_market_data_influx
    ):
        """Test processing handles empty data for fundamentals_queue."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "data": {"datetime": []},  # Empty datetime array
        }

        queue_config = {"name": "fundamentals_queue", "table": "fundamentals"}
        processed, failed = process_queue(
            queue_config,
            mock_queue_broker,
            publisher.influx_clients["fundamentals_queue"],
            lambda: True,
            publisher.logger,
        )

        assert processed == 0
        assert failed == 1
        mock_queue_broker.delete_data.assert_called_once_with("fundamentals_queue", "item1")
        mock_market_data_influx["instance"].write.assert_not_called()


class TestInfluxPublisherSignalHandling:
    """Test signal handling."""

    def test_signal_handler_sets_running_false(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test signal handler sets running flag to False."""
        publisher = InfluxPublisher(temp_config_file)
        publisher.running = True

        publisher._signal_handler(signal.SIGTERM, None)

        assert publisher.running is False

    def test_signal_handler_logs_message(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test signal handler logs shutdown message."""
        publisher = InfluxPublisher(temp_config_file)

        publisher._signal_handler(signal.SIGTERM, None)

        # Check that logger.info was called - the logger instance is publisher.logger
        publisher.logger.info.assert_called()
        assert "SIGTERM" in str(publisher.logger.info.call_args)


class TestInfluxPublisherRun:
    """Test daemon run loop."""

    @pytest.fixture
    def publisher(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Create publisher instance for testing."""
        return InfluxPublisher(temp_config_file)

    @pytest.mark.timeout(10)
    def test_run_processes_queues(self, publisher, mock_queue_broker, mock_market_data_influx):
        """Test run loop processes configured queues."""
        mock_queue_broker.get_queue_size.return_value = 0

        publisher.running = True

        # Run in a thread to allow timeout
        def stop_after_delay():
            time.sleep(0.1)
            publisher.running = False

        thread = threading.Thread(target=stop_after_delay)
        thread.start()

        publisher.run()

        thread.join(timeout=1.0)

    @pytest.mark.timeout(10)
    def test_run_handles_exceptions(self, publisher, mock_queue_broker):
        """Test run loop handles exceptions gracefully."""
        mock_queue_broker.get_queue_size.side_effect = Exception("Redis error")

        publisher.running = True

        def stop_after_delay():
            time.sleep(0.1)
            publisher.running = False

        thread = threading.Thread(target=stop_after_delay)
        thread.start()

        publisher.run()

        thread.join(timeout=1.0)


class TestInfluxPublisherCleanup:
    """Test cleanup operations."""

    def test_cleanup_closes_all_clients(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test cleanup closes all InfluxDB clients."""
        publisher = InfluxPublisher(temp_config_file)

        publisher._cleanup()

        # Verify close was called for each client
        assert mock_market_data_influx["instance"].close.call_count >= 1

    def test_cleanup_handles_close_errors(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test cleanup handles client close errors gracefully."""
        mock_market_data_influx["instance"].close.side_effect = Exception("Close error")

        publisher = InfluxPublisher(temp_config_file)

        # Should not raise exception
        publisher._cleanup()

        # Check that logger.warning was called - the logger instance is publisher.logger
        publisher.logger.warning.assert_called()


class TestInfluxPublisherConstants:
    """Test protected constants."""

    def test_ohlcv_batch_size_constant(self):
        """Test OHLCV_BATCH_SIZE is protected constant."""
        assert OHLCV_BATCH_SIZE == 100_000

    def test_fundamentals_batch_size_constant(self):
        """Test FUNDAMENTALS_BATCH_SIZE constant."""
        assert FUNDAMENTALS_BATCH_SIZE == 50_000

    def test_trading_journal_batch_size_constant(self):
        """Test TRADING_JOURNAL_BATCH_SIZE constant."""
        assert TRADING_JOURNAL_BATCH_SIZE == 50_000

    def test_database_constants(self):
        """Test database name constants."""
        assert OHLCV_DATABASE == "ohlcv"
        assert FUNDAMENTALS_DATABASE == "algo-trader-fundamentals"
        # TRADING_JOURNAL_DATABASE is a backward-compatible alias for BACKTEST_DATABASE
        assert TRADING_JOURNAL_DATABASE == BACKTEST_DATABASE
        # BACKTEST_DATABASE defaults to "backtest-dev" unless INFLUXDB3_ENVIRONMENT=prod
        assert BACKTEST_DATABASE in ("backtest", "backtest-dev")


class TestInfluxPublisherMain:
    """Test main entry point."""

    def test_main_uses_env_var(
        self,
        temp_config_file,
        mock_publisher_logger,
        mock_queue_broker,
        mock_market_data_influx,
        mock_signal,
    ):
        """Test main uses PUBLISHER_CONFIG environment variable."""
        with patch.dict(os.environ, {"PUBLISHER_CONFIG": temp_config_file}):
            with patch(
                "system.algo_trader.influx.publisher.publisher.InfluxPublisher"
            ) as mock_publisher_class:
                mock_publisher = MagicMock()
                mock_publisher_class.return_value = mock_publisher

                main()

                mock_publisher_class.assert_called_once_with(temp_config_file)
                mock_publisher.run.assert_called_once()

    def test_main_uses_default_path(
        self, mock_publisher_logger, mock_queue_broker, mock_market_data_influx, mock_signal
    ):
        """Test main uses default config path when env var not set."""
        default_path = "/app/system/algo_trader/influx/publisher_config.yaml"

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "system.algo_trader.influx.publisher.publisher.InfluxPublisher"
            ) as mock_publisher_class:
                mock_publisher = MagicMock()
                mock_publisher_class.return_value = mock_publisher

                main()

                mock_publisher_class.assert_called_once_with(default_path)
