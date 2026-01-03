"""Unit and E2E tests for publisher __main__ entry point.

Tests cover config path resolution, environment variable handling, config file
validation, error handling, and complete publisher workflow. All external
dependencies are mocked via conftest.py. E2E tests use 'debug' database.
"""

import importlib
import importlib.util
import os
import os.path
import pkgutil
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestMainConfigPath:
    """Test config path resolution."""

    @pytest.mark.unit
    def test_main_default_config_path(self):
        """Test default config path when env var not set."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("os.path.exists", return_value=True),
            patch(
                "system.algo_trader.influx.publisher.publisher.InfluxPublisher"
            ) as mock_publisher_class,
        ):
            mock_publisher = MagicMock()
            mock_publisher_class.return_value = mock_publisher

            # Execute __main__.py by importing and executing it
            with patch("sys.exit"):
                # Clear module cache to ensure fresh import
                if "system.algo_trader.influx.publisher.__main__" in sys.modules:
                    del sys.modules["system.algo_trader.influx.publisher.__main__"]
                # Import the parent package to get access to __main__
                parent_package = importlib.import_module("system.algo_trader.influx.publisher")
                # Find the __main__.py file using pkgutil
                main_file = None
                for importer, modname, _ispkg in pkgutil.iter_modules(
                    parent_package.__path__, parent_package.__name__ + "."
                ):
                    if modname.endswith(".__main__"):
                        # Found the __main__ module, get its file path
                        loader = importer.find_module("__main__")
                        if loader:
                            main_file = loader.get_filename("__main__")
                            break
                # Fallback: try constructing path directly
                if not main_file or not os.path.exists(main_file):
                    main_file = os.path.join(parent_package.__path__[0], "__main__.py")
                # Execute the main block by reading and executing with __name__ = "__main__"
                spec = importlib.util.spec_from_file_location("__main__", main_file)
                main_module = importlib.util.module_from_spec(spec)
                main_module.__name__ = "__main__"
                spec.loader.exec_module(main_module)

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
            patch(
                "system.algo_trader.influx.publisher.publisher.InfluxPublisher"
            ) as mock_publisher_class,
        ):
            mock_publisher = MagicMock()
            mock_publisher_class.return_value = mock_publisher

            # Execute __main__.py by importing and executing it
            with patch("sys.exit"):
                # Clear module cache to ensure fresh import
                if "system.algo_trader.influx.publisher.__main__" in sys.modules:
                    del sys.modules["system.algo_trader.influx.publisher.__main__"]
                # Import the parent package to get access to __main__
                parent_package = importlib.import_module("system.algo_trader.influx.publisher")
                # Find the __main__.py file using pkgutil
                main_file = None
                for importer, modname, _ispkg in pkgutil.iter_modules(
                    parent_package.__path__, parent_package.__name__ + "."
                ):
                    if modname.endswith(".__main__"):
                        # Found the __main__ module, get its file path
                        loader = importer.find_module("__main__")
                        if loader:
                            main_file = loader.get_filename("__main__")
                            break
                # Fallback: try constructing path directly
                if not main_file or not os.path.exists(main_file):
                    main_file = os.path.join(parent_package.__path__[0], "__main__.py")
                # Execute the main block by reading and executing with __name__ = "__main__"
                spec = importlib.util.spec_from_file_location("__main__", main_file)
                main_module = importlib.util.module_from_spec(spec)
                main_module.__name__ = "__main__"
                spec.loader.exec_module(main_module)

            mock_publisher_class.assert_called_once_with(custom_path)

    @pytest.mark.unit
    def test_main_config_file_not_found(self):
        """Test handling missing config file."""
        with (
            patch("os.path.exists", return_value=False),
            patch("builtins.print") as mock_print,
            patch("sys.exit") as mock_exit,
        ):
            mock_exit.side_effect = SystemExit
            # Clear module cache to ensure fresh import
            if "system.algo_trader.influx.publisher.__main__" in sys.modules:
                del sys.modules["system.algo_trader.influx.publisher.__main__"]
            with pytest.raises(SystemExit):
                # Import the parent package to get access to __main__
                parent_package = importlib.import_module("system.algo_trader.influx.publisher")
                # Find the __main__.py file using pkgutil
                main_file = None
                for importer, modname, _ispkg in pkgutil.iter_modules(
                    parent_package.__path__, parent_package.__name__ + "."
                ):
                    if modname.endswith(".__main__"):
                        # Found the __main__ module, get its file path
                        loader = importer.find_module("__main__")
                        if loader:
                            main_file = loader.get_filename("__main__")
                            break
                # Fallback: try constructing path directly
                if not main_file or not os.path.exists(main_file):
                    main_file = os.path.join(parent_package.__path__[0], "__main__.py")
                # Execute the main block by reading and executing with __name__ = "__main__"
                spec = importlib.util.spec_from_file_location("__main__", main_file)
                main_module = importlib.util.module_from_spec(spec)
                main_module.__name__ = "__main__"
                spec.loader.exec_module(main_module)

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
            patch(
                "system.algo_trader.influx.publisher.publisher.InfluxPublisher"
            ) as mock_publisher_class,
        ):
            mock_publisher = MagicMock()
            mock_publisher_class.return_value = mock_publisher

            # Execute __main__.py by importing and executing it
            with patch("sys.exit"):
                # Clear module cache to ensure fresh import
                if "system.algo_trader.influx.publisher.__main__" in sys.modules:
                    del sys.modules["system.algo_trader.influx.publisher.__main__"]
                # Import the parent package to get access to __main__
                parent_package = importlib.import_module("system.algo_trader.influx.publisher")
                # Find the __main__.py file using pkgutil
                main_file = None
                for importer, modname, _ispkg in pkgutil.iter_modules(
                    parent_package.__path__, parent_package.__name__ + "."
                ):
                    if modname.endswith(".__main__"):
                        # Found the __main__ module, get its file path
                        loader = importer.find_module("__main__")
                        if loader:
                            main_file = loader.get_filename("__main__")
                            break
                # Fallback: try constructing path directly
                if not main_file or not os.path.exists(main_file):
                    main_file = os.path.join(parent_package.__path__[0], "__main__.py")
                # Execute the main block by reading and executing with __name__ = "__main__"
                spec = importlib.util.spec_from_file_location("__main__", main_file)
                main_module = importlib.util.module_from_spec(spec)
                main_module.__name__ = "__main__"
                spec.loader.exec_module(main_module)

            mock_publisher_class.assert_called_once_with(config_path)
            mock_publisher.run.assert_called_once()

    @pytest.mark.unit
    def test_main_publisher_exception(self):
        """Test handling publisher exceptions."""
        config_path = "/path/to/config.yaml"
        with (
            patch.dict(os.environ, {"PUBLISHER_CONFIG_PATH": config_path}),
            patch("os.path.exists", return_value=True),
            patch(
                "system.algo_trader.influx.publisher.publisher.InfluxPublisher"
            ) as mock_publisher_class,
        ):
            mock_publisher = MagicMock()
            mock_publisher.run.side_effect = Exception("Publisher error")
            mock_publisher_class.return_value = mock_publisher

            # Should propagate exception
            with patch("sys.exit"):
                # Clear module cache to ensure fresh import
                if "system.algo_trader.influx.publisher.__main__" in sys.modules:
                    del sys.modules["system.algo_trader.influx.publisher.__main__"]
                with pytest.raises(Exception, match="Publisher error"):
                    # Import the parent package to get access to __main__
                    parent_package = importlib.import_module("system.algo_trader.influx.publisher")
                    # Get the __main__ module file path
                    main_file = parent_package.__path__[0] + "/__main__.py"
                    # Execute the main block by reading and executing with __name__ = "__main__"
                    spec = importlib.util.spec_from_file_location("__main__", main_file)
                    main_module = importlib.util.module_from_spec(spec)
                    main_module.__name__ = "__main__"
                    spec.loader.exec_module(main_module)
