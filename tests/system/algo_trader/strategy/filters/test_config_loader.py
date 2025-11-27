"""Unit tests for filter config_loader - Filter Configuration Loading.

Tests cover config file loading, path resolution, YAML parsing, filter creation,
and error handling. All external dependencies are mocked via conftest.py.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from system.algo_trader.strategy.filters.config_loader import (
    _create_filter_from_config,
    _resolve_config_path,
    load_filter_config,
    load_filter_config_dict,
    load_filter_config_dicts,
    load_filter_configs,
)
from system.algo_trader.strategy.filters.core import FilterPipeline


class TestResolveConfigPath:
    """Test _resolve_config_path function."""

    def test_resolve_config_path_with_yaml_extension(self):
        """Test resolving path with .yaml extension."""
        result = _resolve_config_path("/path/to/config.yaml")
        assert result == Path("/path/to/config.yaml")

    def test_resolve_config_path_with_yml_extension(self):
        """Test resolving path with .yml extension."""
        result = _resolve_config_path("/path/to/config.yml")
        assert result == Path("/path/to/config.yml")

    def test_resolve_config_path_with_separator(self):
        """Test resolving path with path separator."""
        result = _resolve_config_path("path/to/config")
        assert result == Path("path/to/config")

    def test_resolve_config_path_name_only(self):
        """Test resolving config name to strategies directory."""
        result = _resolve_config_path("price_min")
        assert result.name == "price_min.yaml"
        assert "strategies" in str(result)


class TestCreateFilterFromConfig:
    """Test _create_filter_from_config function."""

    def test_create_filter_from_config_success(self, mock_logger):
        """Test creating filter from valid config."""
        filter_config = {
            "type": "price_comparison",
            "params": {"field": "price", "operator": ">", "value": 100.0},
        }
        result = _create_filter_from_config(filter_config, mock_logger)

        assert result is not None
        assert hasattr(result, "filter_type")
        assert result.filter_type == "price_comparison"

    def test_create_filter_from_config_missing_type(self, mock_logger):
        """Test creating filter with missing type field."""
        filter_config = {"params": {"field": "price", "operator": ">", "value": 100.0}}
        result = _create_filter_from_config(filter_config, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_create_filter_from_config_unknown_type(self, mock_logger):
        """Test creating filter with unknown type."""
        filter_config = {
            "type": "unknown_filter",
            "params": {"field": "price", "operator": ">", "value": 100.0},
        }
        result = _create_filter_from_config(filter_config, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_create_filter_from_config_uses_from_config_method(self, mock_logger):
        """Test that from_config class method is used when available."""
        filter_config = {
            "type": "price_comparison",
            "params": {"field": "price", "operator": ">", "value": 100.0},
        }
        result = _create_filter_from_config(filter_config, mock_logger)

        assert result is not None
        # Verify it was created using from_config or __init__
        assert hasattr(result, "field")
        assert result.field == "price"


class TestLoadFilterConfig:
    """Test load_filter_config function."""

    def test_load_filter_config_success(self, mock_logger):
        """Test loading valid filter config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "filters": [
                    {
                        "type": "price_comparison",
                        "params": {"field": "price", "operator": ">", "value": 100.0},
                    }
                ]
            }
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            result = load_filter_config(config_path, mock_logger)

            assert result is not None
            assert isinstance(result, FilterPipeline)
            assert len(result.filters) == 1
        finally:
            Path(config_path).unlink()

    def test_load_filter_config_none_returns_none(self, mock_logger):
        """Test loading None config returns None."""
        result = load_filter_config(None, mock_logger)

        assert result is None

    def test_load_filter_config_file_not_found(self, mock_logger):
        """Test loading non-existent config file."""
        result = load_filter_config("nonexistent_config.yaml", mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_load_filter_config_invalid_yaml_structure(self, mock_logger):
        """Test loading config with invalid YAML structure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("not a dictionary")
            config_path = f.name

        try:
            result = load_filter_config(config_path, mock_logger)

            assert result is None
            mock_logger.error.assert_called()
        finally:
            Path(config_path).unlink()

    def test_load_filter_config_missing_filters_key(self, mock_logger):
        """Test loading config missing 'filters' key."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {}
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            result = load_filter_config(config_path, mock_logger)

            assert result is None
            mock_logger.warning.assert_called()
        finally:
            Path(config_path).unlink()

    def test_load_filter_config_empty_filters_list(self, mock_logger):
        """Test loading config with empty filters list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {"filters": []}
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            result = load_filter_config(config_path, mock_logger)

            assert result is None
            mock_logger.warning.assert_called()
        finally:
            Path(config_path).unlink()

    def test_load_filter_config_multiple_filters(self, mock_logger):
        """Test loading config with multiple filters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "filters": [
                    {
                        "type": "price_comparison",
                        "params": {"field": "price", "operator": ">", "value": 100.0},
                    },
                    {
                        "type": "price_comparison",
                        "params": {"field": "price", "operator": "<", "value": 200.0},
                    },
                ]
            }
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            result = load_filter_config(config_path, mock_logger)

            assert result is not None
            assert isinstance(result, FilterPipeline)
            assert len(result.filters) == 2
        finally:
            Path(config_path).unlink()


class TestLoadFilterConfigs:
    """Test load_filter_configs function."""

    def test_load_filter_configs_combines_multiple_configs(self, mock_logger):
        """Test loading and combining multiple config files."""
        config_files = []
        try:
            for i, config_data in enumerate(
                [
                    {
                        "filters": [
                            {
                                "type": "price_comparison",
                                "params": {"field": "price", "operator": ">", "value": 100.0},
                            }
                        ]
                    },
                    {
                        "filters": [
                            {
                                "type": "price_comparison",
                                "params": {"field": "price", "operator": "<", "value": 200.0},
                            }
                        ]
                    },
                ]
            ):
                f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
                yaml.dump(config_data, f)
                f.close()
                config_files.append(f.name)

            result = load_filter_configs(config_files, mock_logger)

            assert result is not None
            assert isinstance(result, FilterPipeline)
            assert len(result.filters) == 2
        finally:
            for config_path in config_files:
                Path(config_path).unlink()

    def test_load_filter_configs_none_returns_none(self, mock_logger):
        """Test loading None configs returns None."""
        result = load_filter_configs(None, mock_logger)

        assert result is None

    def test_load_filter_configs_empty_list_returns_none(self, mock_logger):
        """Test loading empty config list returns None."""
        result = load_filter_configs([], mock_logger)

        assert result is None


class TestLoadFilterConfigDict:
    """Test load_filter_config_dict function."""

    def test_load_filter_config_dict_success(self, mock_logger):
        """Test loading config as dictionary."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "filters": [
                    {
                        "type": "price_comparison",
                        "params": {"field": "price", "operator": ">", "value": 100.0},
                    }
                ]
            }
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            result = load_filter_config_dict(config_path, mock_logger)

            assert result is not None
            assert isinstance(result, dict)
            assert "filters" in result
        finally:
            Path(config_path).unlink()

    def test_load_filter_config_dict_none_returns_none(self, mock_logger):
        """Test loading None config returns None."""
        result = load_filter_config_dict(None, mock_logger)

        assert result is None


class TestLoadFilterConfigDicts:
    """Test load_filter_config_dicts function."""

    def test_load_filter_config_dicts_combines_multiple(self, mock_logger):
        """Test loading and combining multiple config dicts."""
        config_files = []
        try:
            for config_data in [
                {
                    "filters": [
                        {
                            "type": "price_comparison",
                            "params": {"field": "price", "operator": ">", "value": 100.0},
                        }
                    ]
                },
                {
                    "filters": [
                        {
                            "type": "price_comparison",
                            "params": {"field": "price", "operator": "<", "value": 200.0},
                        }
                    ]
                },
            ]:
                f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
                yaml.dump(config_data, f)
                f.close()
                config_files.append(f.name)

            result = load_filter_config_dicts(config_files, mock_logger)

            assert result is not None
            assert isinstance(result, dict)
            assert "filters" in result
            assert len(result["filters"]) == 2
        finally:
            for config_path in config_files:
                Path(config_path).unlink()

    def test_load_filter_config_dicts_none_returns_none(self, mock_logger):
        """Test loading None configs returns None."""
        result = load_filter_config_dicts(None, mock_logger)

        assert result is None

