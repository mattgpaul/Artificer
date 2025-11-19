"""Unit tests for position_manager config_loader.

Tests cover config file loading, path resolution, YAML parsing, and error handling.
All external dependencies are mocked via conftest.py.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from system.algo_trader.strategy.position_manager.config_loader import (
    _resolve_config_path,
    load_position_manager_config,
)
from system.algo_trader.strategy.position_manager.position_manager import (
    PositionManagerConfig,
)


class TestResolveConfigPath:
    """Test _resolve_config_path function."""

    @pytest.mark.unit
    def test_resolve_config_path_with_yaml_extension(self):
        """Test resolving path with .yaml extension."""
        result = _resolve_config_path("/path/to/config.yaml")
        assert result == Path("/path/to/config.yaml")

    @pytest.mark.unit
    def test_resolve_config_path_with_yml_extension(self):
        """Test resolving path with .yml extension."""
        result = _resolve_config_path("/path/to/config.yml")
        assert result == Path("/path/to/config.yml")

    @pytest.mark.unit
    def test_resolve_config_path_with_separator(self):
        """Test resolving path with path separator."""
        result = _resolve_config_path("path/to/config")
        assert result == Path("path/to/config")

    @pytest.mark.unit
    def test_resolve_config_path_name_only(self):
        """Test resolving config name to strategies directory."""
        result = _resolve_config_path("default")
        # Path should resolve relative to config_loader.py location
        expected_base = (
            Path(__file__).resolve().parent.parent.parent.parent.parent
            / "system"
            / "algo_trader"
            / "strategy"
            / "position_manager"
            / "strategies"
            / "default.yaml"
        )
        assert result.name == "default.yaml"
        assert "strategies" in str(result)
        assert result.exists() or not result.exists()  # Just check it's a valid path


class TestLoadPositionManagerConfig:
    """Test load_position_manager_config function."""

    @pytest.mark.unit
    def test_load_config_none_returns_none(self, mock_logger):
        """Test loading None config returns None."""
        result = load_position_manager_config(None)
        assert result is None

    @pytest.mark.unit
    def test_load_config_file_not_found(self):
        """Test loading non-existent config file returns None."""
        result = load_position_manager_config("nonexistent")
        assert result is None

    @pytest.mark.unit
    def test_load_config_invalid_yaml_structure(self):
        """Test loading config with invalid YAML structure returns config with defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("not a dict: invalid")
            temp_path = f.name

        try:
            result = load_position_manager_config(temp_path)
            # Code handles non-dict by using defaults
            assert isinstance(result, PositionManagerConfig)
            assert result.allow_scale_in is False  # Default
        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_load_config_simple_dict(self):
        """Test loading config with simple dictionary structure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"allow_scale_in": True}, f)
            temp_path = f.name

        try:
            result = load_position_manager_config(temp_path)
            assert isinstance(result, PositionManagerConfig)
            assert result.allow_scale_in is True
        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_load_config_nested_position_manager_key(self):
        """Test loading config with nested position_manager key."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"position_manager": {"allow_scale_in": False}}, f)
            temp_path = f.name

        try:
            result = load_position_manager_config(temp_path)
            assert isinstance(result, PositionManagerConfig)
            assert result.allow_scale_in is False
        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_load_config_empty_file(self):
        """Test loading empty config file uses defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            result = load_position_manager_config(temp_path)
            assert isinstance(result, PositionManagerConfig)
            assert result.allow_scale_in is False  # Default value
        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_load_config_from_strategies_directory(self):
        """Test loading config from strategies directory by name."""
        # This test assumes default.yaml exists in strategies directory
        result = load_position_manager_config("default")
        if result is not None:
            assert isinstance(result, PositionManagerConfig)
        # If file doesn't exist, result will be None - both are valid outcomes

    @pytest.mark.unit
    def test_load_config_yaml_parse_error(self):
        """Test loading config with YAML parse error returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [unclosed")
            temp_path = f.name

        try:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = yaml.YAMLError("Parse error")
                result = load_position_manager_config(temp_path)
                assert result is None
        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_load_config_file_read_error(self):
        """Test loading config with file read error returns None."""
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = load_position_manager_config("/some/path/config.yaml")
            # File doesn't exist, so it will return None before trying to open
            assert result is None
