"""Unit tests for publisher config module.

Tests cover config loading, namespace extraction, InfluxDB client initialization,
database mapping, batch size configuration, and protected constants validation.
All external dependencies are mocked.
"""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from system.algo_trader.influx.publisher.config import (
    FUNDAMENTALS_BATCH_SIZE,
    FUNDAMENTALS_DATABASE,
    OHLCV_BATCH_SIZE,
    OHLCV_DATABASE,
    get_namespace,
    init_influx_clients,
    load_config,
)


class TestLoadConfig:
    """Test load_config function."""

    @pytest.mark.unit
    def test_load_config_valid_file(self):
        """Test loading valid config file."""
        config_content = """
queues:
  - name: ohlcv_queue
    table: ohlcv
    namespace: queue
"""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=config_content)),
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = load_config("/path/to/config.yaml")

            assert "queues" in result
            assert len(result["queues"]) == 1
            assert result["queues"][0]["name"] == "ohlcv_queue"

    @pytest.mark.unit
    def test_load_config_missing_file(self):
        """Test loading missing config file."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(SystemExit):
                load_config("/path/to/missing.yaml")

    @pytest.mark.unit
    def test_load_config_invalid_yaml(self):
        """Test loading invalid YAML."""
        config_content = "invalid: yaml: content: ["
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=config_content)),
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(SystemExit):
                load_config("/path/to/invalid.yaml")


class TestGetNamespace:
    """Test get_namespace function."""

    @pytest.mark.unit
    def test_get_namespace_from_config(self):
        """Test extracting namespace from config."""
        config = {"queues": [{"name": "ohlcv_queue", "table": "ohlcv", "namespace": "custom"}]}
        result = get_namespace(config)
        assert result == "custom"

    @pytest.mark.unit
    def test_get_namespace_default(self):
        """Test default namespace when not specified."""
        config = {"queues": [{"name": "ohlcv_queue", "table": "ohlcv"}]}
        result = get_namespace(config)
        assert result == "queue"

    @pytest.mark.unit
    def test_get_namespace_empty_config(self):
        """Test default namespace with empty config."""
        config = {}
        result = get_namespace(config)
        assert result == "queue"


class TestInitInfluxClients:
    """Test init_influx_clients function."""

    @pytest.mark.unit
    def test_init_influx_clients_ohlcv_queue(self):
        """Test initializing client for OHLCV queue."""
        config = {
            "queues": [
                {
                    "name": "ohlcv_queue",
                    "table": "ohlcv",
                    "flush_interval": 10000,
                }
            ]
        }

        with (
            patch(
                "system.algo_trader.influx.publisher.config.MarketDataInflux"
            ) as mock_client_class,
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = init_influx_clients(config)

            assert "ohlcv_queue" in result
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args[1]["database"] == OHLCV_DATABASE

    @pytest.mark.unit
    def test_init_influx_clients_fundamentals_queue(self):
        """Test initializing client for fundamentals queue."""
        config = {
            "queues": [
                {
                    "name": "fundamentals_queue",
                    "table": "fundamentals",
                }
            ]
        }

        with (
            patch(
                "system.algo_trader.influx.publisher.config.MarketDataInflux"
            ) as mock_client_class,
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = init_influx_clients(config)

            assert "fundamentals_queue" in result
            call_args = mock_client_class.call_args
            assert call_args[1]["database"] == FUNDAMENTALS_DATABASE

    @pytest.mark.unit
    def test_init_influx_clients_backtest_queues(self):
        """Test initializing clients for backtest queues."""
        config = {
            "queues": [
                {"name": "backtest_trades_queue", "table": "backtest_trades"},
                {"name": "backtest_metrics_queue", "table": "backtest_metrics"},
            ]
        }

        with (
            patch(
                "system.algo_trader.influx.publisher.config.MarketDataInflux"
            ) as mock_client_class,
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = init_influx_clients(config)

            assert "backtest_trades_queue" in result
            assert "backtest_metrics_queue" in result
            assert mock_client_class.call_count == 2

    @pytest.mark.unit
    def test_init_influx_clients_unknown_queue(self):
        """Test handling unknown queue name."""
        config = {"queues": [{"name": "unknown_queue", "table": "unknown"}]}

        with (
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(SystemExit):
                init_influx_clients(config)

    @pytest.mark.unit
    def test_init_influx_clients_ohlcv_batch_size_protected(self):
        """Test OHLCV batch size is protected."""
        config = {
            "queues": [
                {
                    "name": "ohlcv_queue",
                    "table": "ohlcv",
                    "batch_size": 100000,  # Wrong batch size
                }
            ]
        }

        with (
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # Should use OHLCV_BATCH_SIZE constant regardless of config
            with patch(
                "system.algo_trader.influx.publisher.config.MarketDataInflux"
            ) as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                init_influx_clients(config)

                # Should still work, using protected constant
                call_args = mock_client_class.call_args
                write_config = call_args[1]["write_config"]
                assert write_config.batch_size == OHLCV_BATCH_SIZE

    @pytest.mark.unit
    def test_init_influx_clients_batch_size_config(self):
        """Test batch size configuration."""
        config = {
            "queues": [
                {
                    "name": "fundamentals_queue",
                    "table": "fundamentals",
                    "batch_size": FUNDAMENTALS_BATCH_SIZE,
                }
            ]
        }

        with (
            patch(
                "system.algo_trader.influx.publisher.config.MarketDataInflux"
            ) as mock_client_class,
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            init_influx_clients(config)

            call_args = mock_client_class.call_args
            write_config = call_args[1]["write_config"]
            assert write_config.batch_size == FUNDAMENTALS_BATCH_SIZE

    @pytest.mark.unit
    def test_init_influx_clients_write_config_parameters(self):
        """Test write config parameters."""
        config = {
            "queues": [
                {
                    "name": "ohlcv_queue",
                    "table": "ohlcv",
                    "flush_interval": 5000,
                    "jitter_interval": 1000,
                    "retry_interval": 10000,
                    "max_retries": 3,
                    "max_retry_delay": 20000,
                    "exponential_base": 1.5,
                }
            ]
        }

        with (
            patch(
                "system.algo_trader.influx.publisher.config.MarketDataInflux"
            ) as mock_client_class,
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            init_influx_clients(config)

            call_args = mock_client_class.call_args
            write_config = call_args[1]["write_config"]
            assert write_config.flush_interval == 5000
            assert write_config.jitter_interval == 1000
            assert write_config.retry_interval == 10000
            assert write_config.max_retries == 3
            assert write_config.max_retry_delay == 20000
            assert write_config.exponential_base == 1.5

    @pytest.mark.unit
    def test_init_influx_clients_multiple_queues(self):
        """Test initializing multiple queue clients."""
        config = {
            "queues": [
                {"name": "ohlcv_queue", "table": "ohlcv"},
                {"name": "fundamentals_queue", "table": "fundamentals"},
                {"name": "trading_journal_queue", "table": "trading_journal"},
            ]
        }

        with (
            patch(
                "system.algo_trader.influx.publisher.config.MarketDataInflux"
            ) as mock_client_class,
            patch("system.algo_trader.influx.publisher.config.get_logger") as mock_get_logger,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = init_influx_clients(config)

            assert len(result) == 3
            assert "ohlcv_queue" in result
            assert "fundamentals_queue" in result
            assert "trading_journal_queue" in result
            assert mock_client_class.call_count == 3
