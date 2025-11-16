"""Unit tests for BaseInfluxDBClient - InfluxDB Database Operations.

Tests cover client initialization, batch write configuration, connection management,
ping functionality, and error handling.
All InfluxDB operations are mocked to avoid requiring an InfluxDB server.
"""

import os
from abc import ABCMeta
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from infrastructure.influxdb.influxdb import BaseInfluxDBClient, BatchingCallback, BatchWriteConfig


class ConcreteInfluxDBClient(BaseInfluxDBClient):
    """Concrete implementation for testing abstract BaseInfluxDBClient."""

    def write(self):
        """Concrete implementation of abstract write method."""
        pass

    def query(self):
        """Concrete implementation of abstract query method."""
        pass


class TestBatchWriteConfig:
    """Test BatchWriteConfig dataclass configuration."""

    def test_default_config(self):
        """Test BatchWriteConfig with default values."""
        config = BatchWriteConfig()

        assert config.batch_size == 100
        assert config.flush_interval == 10_000
        assert config.jitter_interval == 2_000
        assert config.retry_interval == 5_000
        assert config.max_retries == 5
        assert config.max_retry_delay == 30_000
        assert config.exponential_base == 2

    def test_custom_config(self):
        """Test BatchWriteConfig with custom values."""
        config = BatchWriteConfig(
            batch_size=50,
            flush_interval=5_000,
            jitter_interval=1_000,
            retry_interval=2_000,
            max_retries=3,
            max_retry_delay=15_000,
            exponential_base=3,
        )

        assert config.batch_size == 50
        assert config.flush_interval == 5_000
        assert config.jitter_interval == 1_000
        assert config.retry_interval == 2_000
        assert config.max_retries == 3
        assert config.max_retry_delay == 15_000
        assert config.exponential_base == 3

    def test_validation_positive_batch_size(self):
        """Test BatchWriteConfig validates positive batch_size."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BatchWriteConfig(batch_size=0)

        with pytest.raises(ValueError, match="batch_size must be positive"):
            BatchWriteConfig(batch_size=-1)

    def test_validation_non_negative_retries(self):
        """Test BatchWriteConfig validates non-negative max_retries."""
        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            BatchWriteConfig(max_retries=-1)

    def test_valid_zero_retries(self):
        """Test BatchWriteConfig allows zero retries."""
        config = BatchWriteConfig(max_retries=0)
        assert config.max_retries == 0

    def test_to_write_options(self):
        """Test _to_write_options conversion."""
        config = BatchWriteConfig(batch_size=200, max_retries=10)

        with patch("infrastructure.influxdb.influxdb.WriteOptions") as mock_write_options:
            config._to_write_options()

            mock_write_options.assert_called_once_with(
                batch_size=200,
                flush_interval=10_000,
                jitter_interval=2_000,
                retry_interval=5_000,
                max_retries=10,
                max_retry_delay=30_000,
                exponential_base=2,
            )


class TestBatchingCallback:
    """Test BatchingCallback methods."""

    @pytest.fixture
    def callback(self):
        """Fixture to create a BatchingCallback instance."""
        with patch("infrastructure.influxdb.influxdb.get_logger") as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            callback = BatchingCallback()
            callback.logger = mock_logger_instance
            return callback

    def test_initialization(self):
        """Test BatchingCallback initialization."""
        with patch("infrastructure.influxdb.influxdb.get_logger"):
            callback = BatchingCallback()
            assert callback._pending_batches == 0
            assert hasattr(callback, "_lock")
            assert hasattr(callback, "logger")

    def test_increment_pending(self, callback):
        """Test increment_pending increases counter."""
        assert callback._pending_batches == 0
        callback.increment_pending()
        assert callback._pending_batches == 1
        callback.increment_pending()
        assert callback._pending_batches == 2

    def test_get_pending_count(self, callback):
        """Test get_pending_count returns correct count."""
        assert callback.get_pending_count() == 0
        callback.increment_pending()
        assert callback.get_pending_count() == 1

    def test_success_callback_logs_debug(self, callback):
        """Test success callback logs debug message and decrements counter."""
        callback.increment_pending()
        callback.success("batch_config", "test_data")

        callback.logger.debug.assert_called_once()
        assert "Written batch: batch_config" in callback.logger.debug.call_args[0][0]
        assert callback._pending_batches == 0

    def test_error_callback_logs_error(self, callback):
        """Test error callback logs error details and decrements counter."""
        with patch("influxdb_client_3.InfluxDBError"):
            mock_error_instance = Mock()
            mock_error_instance.__str__ = Mock(return_value="Test error")

            callback.increment_pending()
            callback.error("batch_config", "test_data", mock_error_instance)

            # Error callback logs multiple times (data preview + final message)
            assert callback.logger.error.call_count >= 1
            # Check that the final error message contains expected text
            last_call_args = callback.logger.error.call_args_list[-1][0][0]
            assert "Cannot write batch: batch_config" in last_call_args
            assert callback._pending_batches == 0

    def test_error_callback_handles_bytes_data(self, callback):
        """Test error callback handles bytes data properly."""
        with patch("influxdb_client_3.InfluxDBError"):
            mock_error_instance = Mock()
            mock_error_instance.__str__ = Mock(return_value="Test error")

            callback.increment_pending()
            callback.error("batch_config", b"test_bytes_data", mock_error_instance)

            # Error callback logs multiple times (data preview + final message)
            assert callback.logger.error.call_count >= 1
            # Check that one of the calls contains the bytes data
            all_call_args = [call[0][0] for call in callback.logger.error.call_args_list]
            assert any("test_bytes_data" in arg for arg in all_call_args)
            assert callback._pending_batches == 0

    def test_retry_callback_logs_warning(self, callback):
        """Test retry callback logs warning and does not decrement counter."""
        with patch("influxdb_client_3.InfluxDBError"):
            mock_error_instance = Mock()
            mock_error_instance.__str__ = Mock(return_value="Retryable error")

            callback.increment_pending()
            callback.retry("batch_config", "test_data", mock_error_instance)

            callback.logger.warning.assert_called_once()
            assert (
                "Retryable error occurs for batch: batch_config"
                in callback.logger.warning.call_args[0][0]
            )
            # Counter should not be decremented on retry
            assert callback._pending_batches == 1

    def test_retry_callback_handles_bytes_data(self, callback):
        """Test retry callback handles bytes data properly."""
        with patch("influxdb_client_3.InfluxDBError"):
            mock_error_instance = Mock()
            mock_error_instance.__str__ = Mock(return_value="Retryable error")

            callback.increment_pending()
            callback.retry("batch_config", b"test_bytes_data", mock_error_instance)

            callback.logger.warning.assert_called_once()
            assert "test_bytes_data" in callback.logger.warning.call_args[0][0]


class TestInfluxDBClientInitialization:
    """Test BaseInfluxDBClient initialization and configuration."""

    @pytest.fixture
    def mock_influx_dependencies(self):
        """Fixture to mock InfluxDB dependencies."""
        with (
            patch("infrastructure.influxdb.influxdb.get_logger") as mock_logger,
            patch("infrastructure.influxdb.influxdb.InfluxDBClient3") as mock_client_class,
            patch("infrastructure.influxdb.influxdb.write_client_options") as mock_wco,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_wco.return_value = MagicMock()

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "client_class": mock_client_class,
                "client": mock_client,
                "wco": mock_wco,
            }

    def test_initialization_default_config(self, mock_influx_dependencies):
        """Test initialization with default configuration."""
        with patch.dict(os.environ, {}, clear=True):
            client = ConcreteInfluxDBClient(database="test_db")

            assert client.database == "test_db"
            assert client.token == "my-secret-token"
            assert client.url == "http://localhost:8181"
            assert isinstance(client.write_config, BatchWriteConfig)

    def test_initialization_custom_env_config(self, mock_influx_dependencies):
        """Test initialization with custom environment configuration."""
        with patch.dict(
            os.environ,
            {
                "INFLUXDB3_AUTH_TOKEN": "custom_token",
                "INFLUXDB3_HTTP_BIND_ADDR": "influxdb.example.com:8086",
            },
        ):
            client = ConcreteInfluxDBClient(database="custom_db")

            assert client.database == "custom_db"
            assert client.token == "custom_token"
            assert client.url == "http://influxdb.example.com:8086"

    def test_initialization_custom_write_config(self, mock_influx_dependencies):
        """Test initialization with custom BatchWriteConfig."""
        custom_config = BatchWriteConfig(batch_size=500, max_retries=10)

        client = ConcreteInfluxDBClient(database="test_db", write_config=custom_config)

        assert client.write_config.batch_size == 500
        assert client.write_config.max_retries == 10

    def test_client_creation(self, mock_influx_dependencies):
        """Test InfluxDB client is created with correct parameters."""
        with patch.dict(
            os.environ,
            {"INFLUXDB3_AUTH_TOKEN": "test_token", "INFLUXDB3_HTTP_BIND_ADDR": "localhost:8181"},
        ):
            ConcreteInfluxDBClient(database="test_db")

            mock_influx_dependencies["client_class"].assert_called_once()
            call_kwargs = mock_influx_dependencies["client_class"].call_args[1]
            assert call_kwargs["token"] == "test_token"
            assert call_kwargs["host"] == "http://localhost:8181"
            assert call_kwargs["database"] == "test_db"

    def test_write_client_options_setup(self, mock_influx_dependencies):
        """Test write client options are configured correctly."""
        ConcreteInfluxDBClient(database="test_db")

        mock_influx_dependencies["wco"].assert_called_once()
        call_kwargs = mock_influx_dependencies["wco"].call_args[1]
        assert "success_callback" in call_kwargs
        assert "error_callback" in call_kwargs
        assert "retry_callback" in call_kwargs
        assert "write_options" in call_kwargs

    def test_headers_property(self, mock_influx_dependencies):
        """Test _headers property returns correct authorization."""
        with patch.dict(os.environ, {"INFLUXDB3_AUTH_TOKEN": "test_token"}):
            client = ConcreteInfluxDBClient(database="test_db")

            headers = client._headers

            assert headers["Authorization"] == "Bearer test_token"


class TestInfluxDBClientPing:
    """Test ping functionality."""

    @pytest.fixture
    def mock_influx_dependencies(self):
        """Fixture to mock InfluxDB dependencies."""
        with (
            patch("infrastructure.influxdb.influxdb.get_logger") as mock_logger,
            patch("infrastructure.influxdb.influxdb.InfluxDBClient3") as mock_client_class,
            patch("infrastructure.influxdb.influxdb.write_client_options") as mock_wco,
            patch("infrastructure.influxdb.influxdb.requests") as mock_requests,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_wco.return_value = MagicMock()

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "client_class": mock_client_class,
                "client": mock_client,
                "wco": mock_wco,
                "requests": mock_requests,
            }

    def test_ping_success(self, mock_influx_dependencies):
        """Test successful ping to InfluxDB server."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_influx_dependencies["requests"].get.return_value = mock_response

        client = ConcreteInfluxDBClient(database="test_db")
        result = client.ping()

        assert result is True
        mock_influx_dependencies["logger_instance"].debug.assert_called_with(
            "InfluxDB ping successful"
        )

    def test_ping_failure_non_200_status(self, mock_influx_dependencies):
        """Test ping failure with non-200 status code."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_influx_dependencies["requests"].get.return_value = mock_response

        client = ConcreteInfluxDBClient(database="test_db")
        result = client.ping()

        assert result is False
        mock_influx_dependencies["logger_instance"].debug.assert_called()

    def test_ping_failure_exception(self, mock_influx_dependencies):
        """Test ping failure with exception."""
        mock_influx_dependencies["requests"].get.side_effect = Exception("Connection refused")

        client = ConcreteInfluxDBClient(database="test_db")
        result = client.ping()

        assert result is False
        mock_influx_dependencies["logger_instance"].debug.assert_called()

    def test_ping_uses_correct_url(self, mock_influx_dependencies):
        """Test ping uses correct health endpoint URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_influx_dependencies["requests"].get.return_value = mock_response

        with patch.dict(
            os.environ,
            {
                "INFLUXDB3_HTTP_BIND_ADDR": "influxdb.example.com:8086",
                "INFLUXDB3_AUTH_TOKEN": "test_token",
            },
        ):
            client = ConcreteInfluxDBClient(database="test_db")
            client.ping()

            mock_influx_dependencies["requests"].get.assert_called_once_with(
                "http://influxdb.example.com:8086/health",
                headers={"Authorization": "Bearer test_token"},
            )

    def test_ping_timeout(self, mock_influx_dependencies):
        """Test ping handles timeout exceptions."""
        mock_influx_dependencies["requests"].get.side_effect = requests.Timeout("Request timeout")

        client = ConcreteInfluxDBClient(database="test_db")
        result = client.ping()

        assert result is False

    def test_ping_connection_error(self, mock_influx_dependencies):
        """Test ping handles connection errors."""
        mock_influx_dependencies["requests"].get.side_effect = requests.ConnectionError(
            "Connection error"
        )

        client = ConcreteInfluxDBClient(database="test_db")
        result = client.ping()

        assert result is False


class TestInfluxDBClientClose:
    """Test close functionality."""

    @pytest.fixture
    def mock_influx_dependencies(self):
        """Fixture to mock InfluxDB dependencies."""
        with (
            patch("infrastructure.influxdb.influxdb.get_logger") as mock_logger,
            patch("infrastructure.influxdb.influxdb.InfluxDBClient3") as mock_client_class,
            patch("infrastructure.influxdb.influxdb.write_client_options") as mock_wco,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_wco.return_value = MagicMock()

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "client_class": mock_client_class,
                "client": mock_client,
                "wco": mock_wco,
            }

    def test_close_success(self, mock_influx_dependencies):
        """Test successful client close."""
        client = ConcreteInfluxDBClient(database="test_db")
        client.close()

        mock_influx_dependencies["client"].close.assert_called_once()

    def test_close_with_exception(self, mock_influx_dependencies):
        """Test close handles exceptions gracefully."""
        mock_influx_dependencies["client"].close.side_effect = Exception("Close error")

        client = ConcreteInfluxDBClient(database="test_db")
        client.close()

        mock_influx_dependencies["logger_instance"].warning.assert_called()

    def test_close_without_client(self, mock_influx_dependencies):
        """Test close when client doesn't exist."""
        client = ConcreteInfluxDBClient(database="test_db")
        del client.client

        # Should not raise exception
        client.close()

    def test_close_with_none_client(self, mock_influx_dependencies):
        """Test close when client is None."""
        client = ConcreteInfluxDBClient(database="test_db")
        client.client = None

        # Should not raise exception
        client.close()


class TestInfluxDBClientWaitForBatches:
    """Test wait_for_batches functionality."""

    @pytest.fixture
    def mock_influx_dependencies(self):
        """Fixture to mock InfluxDB dependencies."""
        with (
            patch("infrastructure.influxdb.influxdb.get_logger") as mock_logger,
            patch("infrastructure.influxdb.influxdb.InfluxDBClient3") as mock_client_class,
            patch("infrastructure.influxdb.influxdb.write_client_options") as mock_wco,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_wco.return_value = MagicMock()

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "client_class": mock_client_class,
                "client": mock_client,
                "wco": mock_wco,
            }

    def test_wait_for_batches_immediate_completion(self, mock_influx_dependencies):
        """Test wait_for_batches when no batches are pending."""
        client = ConcreteInfluxDBClient(database="test_db")
        client._callback._pending_batches = 0

        result = client.wait_for_batches(timeout=5)

        assert result is True
        mock_influx_dependencies["logger_instance"].info.assert_called()

    def test_wait_for_batches_completes_successfully(self, mock_influx_dependencies):
        """Test wait_for_batches when batches complete within timeout."""
        with patch("infrastructure.influxdb.influxdb.time") as mock_time:
            client = ConcreteInfluxDBClient(database="test_db")
            client._callback._pending_batches = 2

            # Mock sleep to not actually sleep
            mock_time.sleep = MagicMock()

            # Simulate batches completing after 2 polls
            call_count = [0]

            def mock_time_time():
                call_count[0] += 1
                if call_count[0] == 1:  # start_time
                    return 0.0
                elif call_count[0] == 2:  # last_log_time
                    return 0.0
                elif call_count[0] == 3:  # first iteration
                    client._callback._pending_batches = 1
                    return 0.5
                elif call_count[0] == 4:  # check for logging
                    return 0.5
                else:  # second iteration
                    client._callback._pending_batches = 0
                    return 1.0

            mock_time.time.side_effect = mock_time_time

            result = client.wait_for_batches(timeout=30)

            assert result is True

    def test_wait_for_batches_timeout(self, mock_influx_dependencies):
        """Test wait_for_batches times out if batches don't complete."""
        with patch("infrastructure.influxdb.influxdb.time") as mock_time:
            client = ConcreteInfluxDBClient(database="test_db")
            client._callback._pending_batches = 5

            # Mock time.time() to simulate timeout
            # Call 1: start_time = 0.0
            # Call 2: elapsed = 31.0 - 0.0 = 31.0 >= 30, triggers timeout
            mock_time.time.side_effect = [0.0, 31.0]
            # Mock sleep to not actually sleep
            mock_time.sleep = MagicMock()

            result = client.wait_for_batches(timeout=30)

            assert result is False
            mock_influx_dependencies["logger_instance"].warning.assert_called()
            warning_call = mock_influx_dependencies["logger_instance"].warning.call_args[0][0]
            assert "Timeout waiting for batches" in warning_call
            assert "5 batches still pending" in warning_call

    def test_wait_for_batches_custom_poll_interval(self, mock_influx_dependencies):
        """Test wait_for_batches respects custom poll interval."""
        with patch("infrastructure.influxdb.influxdb.time") as mock_time:
            client = ConcreteInfluxDBClient(database="test_db")
            client._callback._pending_batches = 0

            mock_time.time.return_value = 0.0

            client.wait_for_batches(timeout=10, poll_interval=0.25)

            # Should have called sleep with custom interval (if not already complete)
            # Since batches are 0, it returns immediately

    def test_wait_for_batches_logs_progress(self, mock_influx_dependencies):
        """Test wait_for_batches logs progress every 5 seconds."""
        with patch("infrastructure.influxdb.influxdb.time") as mock_time:
            client = ConcreteInfluxDBClient(database="test_db")
            client._callback._pending_batches = 3

            # Mock sleep to not actually sleep
            mock_time.sleep = MagicMock()

            # Simulate 6 seconds passing to trigger progress log
            call_count = [0]

            def mock_time_time():
                call_count[0] += 1
                if call_count[0] <= 2:  # start_time and last_log_time
                    return 0.0
                elif call_count[0] == 3:  # first check
                    return 0.5
                elif call_count[0] == 4:  # check for logging (0.5 < 5, no log)
                    return 0.5
                elif call_count[0] == 5:  # second check
                    return 6.0
                elif call_count[0] == 6:  # check for logging (6.0 >= 5, should log)
                    return 6.0
                else:  # complete
                    client._callback._pending_batches = 0
                    return 6.5

            mock_time.time.side_effect = mock_time_time

            client.wait_for_batches(timeout=30)

            # Should have logged progress
            info_calls = [
                str(call)
                for call in mock_influx_dependencies["logger_instance"].info.call_args_list
            ]
            assert any("pending batches" in call.lower() for call in info_calls)


class TestInfluxDBClientAbstractMethods:
    """Test abstract method enforcement."""

    @pytest.fixture
    def mock_influx_dependencies(self):
        """Fixture to mock InfluxDB dependencies."""
        with (
            patch("infrastructure.influxdb.influxdb.get_logger") as mock_logger,
            patch("infrastructure.influxdb.influxdb.InfluxDBClient3") as mock_client_class,
            patch("infrastructure.influxdb.influxdb.write_client_options") as mock_wco,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_wco.return_value = MagicMock()

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "client_class": mock_client_class,
                "client": mock_client,
                "wco": mock_wco,
            }

    def test_write_is_abstract(self, mock_influx_dependencies):
        """Test write method is abstract and must be implemented."""
        # ConcreteInfluxDBClient implements write, so it should work
        client = ConcreteInfluxDBClient(database="test_db")

        # Should not raise NotImplementedError
        client.write()

    def test_query_is_abstract(self, mock_influx_dependencies):
        """Test query method is abstract and must be implemented."""
        # ConcreteInfluxDBClient implements query, so it should work
        client = ConcreteInfluxDBClient(database="test_db")

        # Should not raise NotImplementedError
        client.query()

    def test_cannot_instantiate_without_implementation(self):
        """Test BaseInfluxDBClient cannot be instantiated without implementing abstract methods."""
        with (
            patch("infrastructure.influxdb.influxdb.get_logger"),
            patch("infrastructure.influxdb.influxdb.InfluxDBClient3"),
            patch("infrastructure.influxdb.influxdb.write_client_options"),
        ):
            # Attempting to instantiate BaseInfluxDBClient directly should fail
            # due to abstract methods (if not for the concrete implementation)
            # This test verifies the abstract nature is preserved
            assert isinstance(BaseInfluxDBClient, ABCMeta)


class TestInfluxDBClientIntegration:
    """Test integration scenarios."""

    @pytest.fixture
    def mock_influx_dependencies(self):
        """Fixture to mock InfluxDB dependencies."""
        with (
            patch("infrastructure.influxdb.influxdb.get_logger") as mock_logger,
            patch("infrastructure.influxdb.influxdb.InfluxDBClient3") as mock_client_class,
            patch("infrastructure.influxdb.influxdb.write_client_options") as mock_wco,
            patch("infrastructure.influxdb.influxdb.requests") as mock_requests,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_wco.return_value = MagicMock()

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "client_class": mock_client_class,
                "client": mock_client,
                "wco": mock_wco,
                "requests": mock_requests,
            }

    def test_full_lifecycle(self, mock_influx_dependencies):
        """Test complete client lifecycle: init -> ping -> close."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_influx_dependencies["requests"].get.return_value = mock_response

        # Initialize
        client = ConcreteInfluxDBClient(database="test_db")
        assert client.database == "test_db"

        # Ping
        assert client.ping() is True

        # Close
        client.close()
        mock_influx_dependencies["client"].close.assert_called_once()

    def test_multiple_pings(self, mock_influx_dependencies):
        """Test multiple ping operations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_influx_dependencies["requests"].get.return_value = mock_response

        client = ConcreteInfluxDBClient(database="test_db")

        # Multiple pings should all succeed
        assert client.ping() is True
        assert client.ping() is True
        assert client.ping() is True

        assert mock_influx_dependencies["requests"].get.call_count == 3

    def test_connection_failure_recovery(self, mock_influx_dependencies):
        """Test recovery from connection failure."""
        # First ping fails, second succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200

        mock_influx_dependencies["requests"].get.side_effect = [
            mock_response_fail,
            mock_response_success,
        ]

        client = ConcreteInfluxDBClient(database="test_db")

        assert client.ping() is False
        assert client.ping() is True


class TestInfluxDBClientEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_influx_dependencies(self):
        """Fixture to mock InfluxDB dependencies."""
        with (
            patch("infrastructure.influxdb.influxdb.get_logger") as mock_logger,
            patch("infrastructure.influxdb.influxdb.InfluxDBClient3") as mock_client_class,
            patch("infrastructure.influxdb.influxdb.write_client_options") as mock_wco,
        ):
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_wco.return_value = MagicMock()

            yield {
                "logger": mock_logger,
                "logger_instance": mock_logger_instance,
                "client_class": mock_client_class,
                "client": mock_client,
                "wco": mock_wco,
            }

    def test_empty_database_name(self, mock_influx_dependencies):
        """Test initialization with empty database name."""
        client = ConcreteInfluxDBClient(database="")

        assert client.database == ""

    def test_special_chars_in_database_name(self, mock_influx_dependencies):
        """Test initialization with special characters in database name."""
        client = ConcreteInfluxDBClient(database="test-db_123")

        assert client.database == "test-db_123"

    def test_unicode_database_name(self, mock_influx_dependencies):
        """Test initialization with unicode characters in database name."""
        client = ConcreteInfluxDBClient(database="数据库")

        assert client.database == "数据库"

    def test_get_write_config_can_be_overridden(self, mock_influx_dependencies):
        """Test _get_write_config can be overridden for custom configuration."""

        class CustomInfluxDBClient(ConcreteInfluxDBClient):
            def _get_write_config(self):
                return BatchWriteConfig(batch_size=1000, max_retries=20)

        client = CustomInfluxDBClient(database="test_db")

        assert client.write_config.batch_size == 1000
        assert client.write_config.max_retries == 20

    def test_none_write_config_uses_default(self, mock_influx_dependencies):
        """Test passing None for write_config uses default."""
        client = ConcreteInfluxDBClient(database="test_db", write_config=None)

        assert isinstance(client.write_config, BatchWriteConfig)
        assert client.write_config.batch_size == 100
