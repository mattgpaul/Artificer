"""Unit and E2E tests for publisher __main__ entry point.

Tests cover config path resolution, environment variable handling, config file
validation, error handling, and complete publisher workflow. All external
dependencies are mocked via conftest.py. E2E tests use 'debug' database.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.influx.publisher import __main__


class TestMainConfigPath:
    """Test config path resolution."""

    @pytest.mark.unit
    def test_main_default_config_path(self):
        """Test default config path when env var not set."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("os.path.exists", return_value=True),
            patch("system.algo_trader.influx.publisher.__main__.InfluxPublisher") as mock_publisher_class,
        ):
            mock_publisher = MagicMock()
            mock_publisher_class.return_value = mock_publisher

            __main__.__main__()

            mock_publisher_class.assert_called_once()
            call_args = mock_publisher_class.call_args
            assert "publisher_config.yaml" in call_args[0][0]

    @pytest.mark.unit
    def test_main_custom_config_path_env(self):
        """Test custom config path from environment variable."""
        custom_path = "/custom/path/config.yaml"
        with (
            patch.dict(os.environ, {"PUBLISHER_CONFIG_PATH": custom_path}),
            patch("os.path.exists", return_value=True),
            patch("system.algo_trader.influx.publisher.__main__.InfluxPublisher") as mock_publisher_class,
        ):
            mock_publisher = MagicMock()
            mock_publisher_class.return_value = mock_publisher

            __main__.__main__()

            mock_publisher_class.assert_called_once_with(custom_path)

    @pytest.mark.unit
    def test_main_config_file_not_found(self):
        """Test handling missing config file."""
        with (
            patch("os.path.exists", return_value=False),
            patch("builtins.print") as mock_print,
        ):
            with pytest.raises(SystemExit):
                __main__.__main__()

            mock_print.assert_called()
            call_args_str = str(mock_print.call_args)
            assert "ERROR" in call_args_str
            assert "not found" in call_args_str


class TestMainPublisherExecution:
    """Test publisher execution."""

    @pytest.mark.e2e
    def test_main_complete_workflow(self):
        """Test complete publisher workflow."""
        config_path = "/path/to/config.yaml"
        with (
            patch.dict(os.environ, {"PUBLISHER_CONFIG_PATH": config_path}),
            patch("os.path.exists", return_value=True),
            patch("system.algo_trader.influx.publisher.__main__.InfluxPublisher") as mock_publisher_class,
        ):
            mock_publisher = MagicMock()
            mock_publisher_class.return_value = mock_publisher

            __main__.__main__()

            mock_publisher_class.assert_called_once_with(config_path)
            mock_publisher.run.assert_called_once()

    @pytest.mark.unit
    def test_main_publisher_exception(self):
        """Test handling publisher exceptions."""
        config_path = "/path/to/config.yaml"
        with (
            patch.dict(os.environ, {"PUBLISHER_CONFIG_PATH": config_path}),
            patch("os.path.exists", return_value=True),
            patch("system.algo_trader.influx.publisher.__main__.InfluxPublisher") as mock_publisher_class,
        ):
            mock_publisher = MagicMock()
            mock_publisher.run.side_effect = Exception("Publisher error")
            mock_publisher_class.return_value = mock_publisher

            # Should propagate exception
            with pytest.raises(Exception, match="Publisher error"):
                __main__.__main__()

