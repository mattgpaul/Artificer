"""Unit tests for company_facts_config - SEC Company Facts Configuration.

Tests cover loading and parsing of company facts metrics configuration from YAML.
All file operations are mocked to avoid requiring actual YAML files.
"""

import io
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from system.algo_trader.datasource.sec.company_facts_config import load_company_facts_config


class TestLoadCompanyFactsConfig:
    """Test company facts configuration loading."""

    @pytest.mark.timeout(10)
    def test_load_company_facts_config_success(self):
        """Test successful configuration loading from YAML."""
        mock_config = {
            "Revenues": {
                "column": "revenue",
                "namespace": "us-gaap",
                "unit_preference": ["USD"],
            },
            "Assets": {
                "column": "total_assets",
                "namespace": "us-gaap",
                "unit_preference": ["USD"],
            },
        }

        mock_file_content = yaml.dump(mock_config)
        # Create a proper file-like object using StringIO that works with yaml.safe_load
        mock_file_obj = io.StringIO(mock_file_content)

        # Mock the entire chain: files() -> joinpath() -> open()
        mock_joinpath = MagicMock()
        mock_joinpath.open.return_value = mock_file_obj
        mock_files = MagicMock()
        mock_files.joinpath.return_value = mock_joinpath

        with patch(
            "system.algo_trader.datasource.sec.company_facts_config.importlib.resources.files",
            return_value=mock_files,
        ):
            result = load_company_facts_config()

            assert isinstance(result, dict)
            assert "Revenues" in result
            assert result["Revenues"]["column"] == "revenue"
            assert result["Revenues"]["namespace"] == "us-gaap"

    @pytest.mark.timeout(10)
    def test_load_company_facts_config_fallback_to_file(self):
        """Test configuration loading falls back to direct file access."""
        mock_config = {
            "Revenues": {
                "column": "revenue",
                "namespace": "us-gaap",
                "unit_preference": ["USD"],
            },
        }

        with (
            patch(
                "system.algo_trader.datasource.sec.company_facts_config.importlib.resources.files"
            ) as mock_files,
            patch("builtins.open", mock_open(read_data=yaml.dump(mock_config))),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.__truediv__", return_value=Path("/fake/path/company_facts.yaml")),
        ):
            # Simulate FileNotFoundError from importlib.resources
            mock_files.side_effect = FileNotFoundError("Resource not found")

            result = load_company_facts_config()

            assert isinstance(result, dict)
            assert "Revenues" in result

    @pytest.mark.timeout(10)
    def test_load_company_facts_config_file_not_found(self):
        """Test configuration loading raises FileNotFoundError when file doesn't exist."""
        with (
            patch(
                "system.algo_trader.datasource.sec.company_facts_config.importlib.resources.files"
            ) as mock_files,
            patch("pathlib.Path.exists", return_value=False),
        ):
            mock_files.side_effect = FileNotFoundError("Resource not found")

            with pytest.raises(FileNotFoundError):
                load_company_facts_config()

    @pytest.mark.timeout(10)
    def test_load_company_facts_config_invalid_yaml(self):
        """Test configuration loading handles invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["

        # Use StringIO for proper file-like object
        mock_file_obj = io.StringIO(invalid_yaml)

        mock_joinpath = MagicMock()
        mock_joinpath.open.return_value = mock_file_obj
        mock_files = MagicMock()
        mock_files.joinpath.return_value = mock_joinpath

        with patch(
            "system.algo_trader.datasource.sec.company_facts_config.importlib.resources.files",
            return_value=mock_files,
        ):
            with pytest.raises(yaml.YAMLError):
                load_company_facts_config()

    @pytest.mark.timeout(10)
    def test_load_company_facts_config_not_dict(self):
        """Test configuration loading raises ValueError when YAML is not a dictionary."""
        invalid_config = ["not", "a", "dict"]

        mock_file_content = yaml.dump(invalid_config)
        # Use StringIO for proper file-like object
        mock_file_obj = io.StringIO(mock_file_content)

        mock_joinpath = MagicMock()
        mock_joinpath.open.return_value = mock_file_obj
        mock_files = MagicMock()
        mock_files.joinpath.return_value = mock_joinpath

        with patch(
            "system.algo_trader.datasource.sec.company_facts_config.importlib.resources.files",
            return_value=mock_files,
        ):
            with pytest.raises(ValueError, match="must contain a dictionary"):
                load_company_facts_config()

    @pytest.mark.timeout(10)
    def test_load_company_facts_config_empty_dict(self):
        """Test configuration loading handles empty dictionary."""
        empty_config = {}

        mock_file_content = yaml.dump(empty_config)
        # Use StringIO for proper file-like object
        mock_file_obj = io.StringIO(mock_file_content)

        mock_joinpath = MagicMock()
        mock_joinpath.open.return_value = mock_file_obj
        mock_files = MagicMock()
        mock_files.joinpath.return_value = mock_joinpath

        with patch(
            "system.algo_trader.datasource.sec.company_facts_config.importlib.resources.files",
            return_value=mock_files,
        ):
            result = load_company_facts_config()

            assert isinstance(result, dict)
            assert len(result) == 0
