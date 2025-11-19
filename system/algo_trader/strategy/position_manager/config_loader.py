"""Configuration loader for position manager.

This module provides functionality to load PositionManagerConfig from YAML
files, supporting both named configs from the strategies directory and
explicit file paths.
"""

from pathlib import Path
from typing import Any

import yaml

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.position_manager.position_manager import (
    PositionManagerConfig,
)


def _resolve_config_path(config_name: str) -> Path:
    """Resolve a position manager config name or path to a concrete file path.

    If the value looks like an explicit path (contains a path separator or ends
    with .yaml/.yml), it is treated as-is. Otherwise it is resolved under the
    local `strategies` directory as `<name>.yaml`.
    """
    candidate = Path(config_name)
    if candidate.suffix in {".yaml", ".yml"} or any(sep in config_name for sep in ("/", "\\")):
        return candidate

    base_dir = Path(__file__).resolve().parent
    strategies_dir = base_dir / "strategies"
    return strategies_dir / f"{config_name}.yaml"


def load_position_manager_config(
    config_name: str | None, logger=None
) -> PositionManagerConfig | None:
    """Load a PositionManagerConfig from a named YAML file or explicit path.

    Args:
        config_name: Either
            - the base name of a YAML file under
              `strategy/position_manager/strategies` (without `.yaml`), or
            - an explicit filesystem path to a YAML file.
        logger: Optional logger instance.
    """
    if config_name is None:
        return None

    logger = logger or get_logger("PositionManagerConfigLoader")

    try:
        config_file = _resolve_config_path(config_name)
        if not config_file.exists():
            logger.error(
                "Position manager config file not found: "
                f"{config_file} (from '{config_name}'). "
                "Expected a file under 'strategy/position_manager/strategies' "
                "or a valid explicit path."
            )
            return None

        with open(config_file, encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

        if not isinstance(config_dict, dict):
            logger.error(f"Position manager config must be a dictionary, got {type(config_dict)}")
            return None

        if "position_manager" in config_dict and isinstance(config_dict["position_manager"], dict):
            position_manager_dict: dict[str, Any] = config_dict["position_manager"]
        else:
            position_manager_dict = config_dict

        config = PositionManagerConfig.from_dict(position_manager_dict)
        logger.info(f"Loaded position manager config from {config_file}: {config.to_dict()}")
        return config

    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(f"Failed to load position manager config: {e}", exc_info=True)
        return None
