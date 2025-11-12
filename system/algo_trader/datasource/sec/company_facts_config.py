"""Load and provide SEC company facts metrics configuration from YAML."""

import importlib.resources
from pathlib import Path
from typing import Any

import yaml


def load_company_facts_config() -> dict[str, dict[str, Any]]:
    """Load the company facts metrics configuration from YAML file.

    Returns:
        Dictionary mapping fact names to their configurations.
        Each configuration contains:
        - column: The column name to use in the output DataFrame
        - namespace: The XBRL namespace (e.g., "us-gaap", "dei")
        - unit_preference: List of preferred unit names (e.g., ["USD"], ["shares"])

    Raises:
        FileNotFoundError: If the YAML configuration file is not found.
        yaml.YAMLError: If the YAML file is malformed.
    """
    try:
        # Use importlib.resources to load the YAML file from the package
        # This works with both regular Python and Bazel runfiles
        with (
            importlib.resources.files("system.algo_trader.datasource.sec")
            .joinpath("company_facts.yaml")
            .open("r", encoding="utf-8") as f
        ):
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ValueError(f"Configuration file must contain a dictionary, got {type(config)}")

        return config
    except FileNotFoundError as err:
        # Fallback for Bazel runfiles or direct file access
        config_path = Path(__file__).parent / "company_facts.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}") from err

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ValueError(
                f"Configuration file must contain a dictionary, got {type(config)}"
            ) from None

        return config
