"""Unit and integration tests for InfluxPublisher.

Tests cover initialization, signal handling, queue monitoring loop, poll interval,
graceful shutdown, cleanup operations, error handling, and complete workflows.
All external dependencies are mocked via conftest.py. Integration tests use
'debug' database.
"""

import signal
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.influx.publisher.publisher import InfluxPublisher


class TestInfluxPublisherInitialization:
    """Test InfluxPublisher initialization."""

    @pytest.mark.unit
    def test_initialization(self, mock_logger):
        """Test publisher initialization."""
        config_path = "/path/to/config.yaml"
        config = {
            "queues": [
                {"name": "ohlcv_queue", "table": "ohlcv", "namespace": "queue"}
            ]
        }

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config") as mock_load_config,
            patch("system.algo_trader.influx.publisher.publisher.get_namespace") as mock_get_namespace,
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal") as mock_signal,
        ):
            mock_load_config.return_value = config
            mock_get_namespace.return_value = "queue"
            mock_init_clients.return_value = {"ohlcv_queue": MagicMock()}
            mock_broker = MagicMock()
            mock_broker_class.return_value = mock_broker

            publisher = InfluxPublisher(config_path)

            assert publisher.running is False
            assert publisher.config == config
            assert publisher.queue_broker == mock_broker
            mock_load_config.assert_called_once_with(config_path, publisher.logger)
            mock_signal.assert_called()

    @pytest.mark.unit
    def test_initialization_signal_handlers(self, mock_logger):
        """Test signal handlers are registered."""
        config_path = "/path/to/config.yaml"
        config = {"queues": [{"name": "ohlcv_queue", "table": "ohlcv"}]}

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal") as mock_signal,
        ):
            mock_init_clients.return_value = {"ohlcv_queue": MagicMock()}
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)

            # Should register SIGTERM and SIGINT handlers
            assert mock_signal.call_count == 2
            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGTERM in signal_calls
            assert signal.SIGINT in signal_calls


class TestInfluxPublisherSignalHandler:
    """Test signal handler functionality."""

    @pytest.mark.unit
    def test_signal_handler_sigterm(self, mock_logger):
        """Test SIGTERM signal handling."""
        config_path = "/path/to/config.yaml"
        config = {"queues": [{"name": "ohlcv_queue", "table": "ohlcv"}]}

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal"),
        ):
            mock_init_clients.return_value = {"ohlcv_queue": MagicMock()}
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)
            publisher.running = True

            publisher._signal_handler(signal.SIGTERM, None)

            assert publisher.running is False

    @pytest.mark.unit
    def test_signal_handler_sigint(self, mock_logger):
        """Test SIGINT signal handling."""
        config_path = "/path/to/config.yaml"
        config = {"queues": [{"name": "ohlcv_queue", "table": "ohlcv"}]}

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal"),
        ):
            mock_init_clients.return_value = {"ohlcv_queue": MagicMock()}
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)
            publisher.running = True

            publisher._signal_handler(signal.SIGINT, None)

            assert publisher.running is False


class TestInfluxPublisherRun:
    """Test run method."""

    @pytest.mark.unit
    def test_run_monitors_queues(self, mock_logger):
        """Test run method monitors configured queues."""
        config_path = "/path/to/config.yaml"
        config = {
            "queues": [
                {"name": "ohlcv_queue", "table": "ohlcv", "poll_interval": 2}
            ]
        }

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal"),
            patch("system.algo_trader.influx.publisher.publisher.process_queue") as mock_process_queue,
            patch("system.algo_trader.influx.publisher.publisher.time.sleep") as mock_sleep,
        ):
            mock_init_clients.return_value = {"ohlcv_queue": MagicMock()}
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)
            publisher.running = True

            # Simulate one iteration then stop
            call_count = 0

            def stop_after_one(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count >= 1:
                    publisher.running = False

            mock_process_queue.side_effect = stop_after_one

            publisher.run()

            mock_process_queue.assert_called()

    @pytest.mark.unit
    def test_run_poll_interval(self, mock_logger):
        """Test poll interval handling."""
        config_path = "/path/to/config.yaml"
        config = {
            "queues": [
                {"name": "ohlcv_queue", "table": "ohlcv", "poll_interval": 5}
            ]
        }

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal"),
            patch("system.algo_trader.influx.publisher.publisher.process_queue") as mock_process_queue,
            patch("system.algo_trader.influx.publisher.publisher.time.sleep") as mock_sleep,
        ):
            mock_init_clients.return_value = {"ohlcv_queue": MagicMock()}
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)
            publisher.running = True

            call_count = 0

            def stop_after_one(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count >= 1:
                    publisher.running = False

            mock_process_queue.side_effect = stop_after_one

            publisher.run()

            # Should sleep with poll_interval
            mock_sleep.assert_called_with(5)

    @pytest.mark.unit
    def test_run_error_handling(self, mock_logger):
        """Test error handling in main loop."""
        config_path = "/path/to/config.yaml"
        config = {
            "queues": [
                {"name": "ohlcv_queue", "table": "ohlcv", "poll_interval": 2}
            ]
        }

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal"),
            patch("system.algo_trader.influx.publisher.publisher.process_queue") as mock_process_queue,
            patch("system.algo_trader.influx.publisher.publisher.time.sleep") as mock_sleep,
        ):
            mock_init_clients.return_value = {"ohlcv_queue": MagicMock()}
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)
            publisher.running = True

            call_count = 0

            def raise_then_stop(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Processing error")
                else:
                    publisher.running = False

            mock_process_queue.side_effect = raise_then_stop

            publisher.run()

            # Should handle error and continue
            mock_logger.error.assert_called()

    @pytest.mark.integration
    def test_run_complete_workflow(self, mock_logger):
        """Test complete publisher workflow."""
        config_path = "/path/to/config.yaml"
        config = {
            "queues": [
                {"name": "ohlcv_queue", "table": "ohlcv", "poll_interval": 2},
                {"name": "fundamentals_queue", "table": "fundamentals", "poll_interval": 2},
            ]
        }

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal"),
            patch("system.algo_trader.influx.publisher.publisher.process_queue") as mock_process_queue,
            patch("system.algo_trader.influx.publisher.publisher.time.sleep") as mock_sleep,
        ):
            mock_init_clients.return_value = {
                "ohlcv_queue": MagicMock(),
                "fundamentals_queue": MagicMock(),
            }
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)
            publisher.running = True

            call_count = 0

            def stop_after_one(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count >= 2:  # Process both queues once
                    publisher.running = False

            mock_process_queue.side_effect = stop_after_one

            publisher.run()

            # Should process both queues
            assert mock_process_queue.call_count >= 2


class TestInfluxPublisherCleanup:
    """Test cleanup operations."""

    @pytest.mark.unit
    def test_cleanup_closes_clients(self, mock_logger):
        """Test cleanup closes all InfluxDB clients."""
        config_path = "/path/to/config.yaml"
        config = {
            "queues": [
                {"name": "ohlcv_queue", "table": "ohlcv"},
                {"name": "fundamentals_queue", "table": "fundamentals"},
            ]
        }

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal"),
        ):
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            mock_init_clients.return_value = {
                "ohlcv_queue": mock_client1,
                "fundamentals_queue": mock_client2,
            }
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)
            publisher._cleanup()

            mock_client1.close.assert_called_once()
            mock_client2.close.assert_called_once()

    @pytest.mark.unit
    def test_cleanup_handles_close_errors(self, mock_logger):
        """Test cleanup handles client close errors gracefully."""
        config_path = "/path/to/config.yaml"
        config = {"queues": [{"name": "ohlcv_queue", "table": "ohlcv"}]}

        with (
            patch("system.algo_trader.influx.publisher.publisher.load_config", return_value=config),
            patch("system.algo_trader.influx.publisher.publisher.get_namespace", return_value="queue"),
            patch("system.algo_trader.influx.publisher.publisher.init_influx_clients") as mock_init_clients,
            patch("system.algo_trader.influx.publisher.publisher.QueueBroker") as mock_broker_class,
            patch("system.algo_trader.influx.publisher.publisher.signal.signal"),
        ):
            mock_client = MagicMock()
            mock_client.close.side_effect = Exception("Close error")
            mock_init_clients.return_value = {"ohlcv_queue": mock_client}
            mock_broker_class.return_value = MagicMock()

            publisher = InfluxPublisher(config_path)
            publisher._cleanup()

            # Should log warning but not raise
            mock_logger.warning.assert_called()

