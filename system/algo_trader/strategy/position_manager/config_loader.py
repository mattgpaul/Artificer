"""Position manager configuration loader.

This module provides functionality to load position manager configurations
from YAML files and create rule pipelines from them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.position_manager.rules.base import AnchorConfig
from system.algo_trader.strategy.position_manager.rules.pipeline import PositionRulePipeline
from system.algo_trader.strategy.position_manager.rules.registry import (
    get_registry as get_position_rule_registry,
)
from system.algo_trader.strategy.position_manager.rules.scaling import ScalingRule
from system.algo_trader.strategy.position_manager.rules.stop_loss import StopLossRule
from system.algo_trader.strategy.position_manager.rules.take_profit import TakeProfitRule


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


def _build_scaling_rule(params: dict[str, Any], logger=None):
    """Build a ScalingRule from configuration parameters.

    Args:
        params: Dictionary of rule-specific parameters.
        logger: Optional logger instance.

    Returns:
        ScalingRule instance.
    """
    allow_scale_in = params.get("allow_scale_in", False)
    allow_scale_out = params.get("allow_scale_out", True)
    return ScalingRule(
        allow_scale_in=allow_scale_in, allow_scale_out=allow_scale_out, logger=logger
    )


def _build_take_profit_rule(params: dict[str, Any], logger=None):
    """Build a TakeProfitRule from configuration parameters.

    Args:
        params: Dictionary of rule-specific parameters.
        logger: Optional logger instance.

    Returns:
        TakeProfitRule instance if successful, None otherwise.
    """
    field_price = params.get("field_price")
    target_pct = params.get("target_pct")
    fraction = params.get("fraction")
    if field_price is None or target_pct is None or fraction is None:
        logger.error("take_profit rule missing required params: field_price, target_pct, fraction")
        return None
    anchor_cfg = params.get("anchor", {}) or {}
    anchor_config = AnchorConfig(
        anchor_type=anchor_cfg.get("type", "entry_price"),
        anchor_field=anchor_cfg.get("field"),
        lookback_bars=int(anchor_cfg["lookback_bars"])
        if anchor_cfg.get("lookback_bars") is not None
        else None,
        one_shot=bool(params.get("one_shot", True)),
    )
    try:
        return TakeProfitRule(
            field_price=field_price,
            target_pct=float(target_pct),
            fraction=float(fraction),
            anchor_config=anchor_config,
            logger=logger,
        )
    except (ValueError, TypeError) as e:
        logger.error(f"take_profit rule params must be numeric where required: {e}")
        return None


def _build_stop_loss_rule(params: dict[str, Any], logger=None):
    """Build a StopLossRule from configuration parameters.

    Args:
        params: Dictionary of rule-specific parameters.
        logger: Optional logger instance.

    Returns:
        StopLossRule instance if successful, None otherwise.
    """
    field_price = params.get("field_price")
    loss_pct = params.get("loss_pct")
    fraction = params.get("fraction")
    if field_price is None or loss_pct is None or fraction is None:
        logger.error("stop_loss rule missing required params: field_price, loss_pct, fraction")
        return None
    anchor_cfg = params.get("anchor", {}) or {}
    anchor_config = AnchorConfig(
        anchor_type=anchor_cfg.get("type", "entry_price"),
        anchor_field=anchor_cfg.get("field"),
        lookback_bars=int(anchor_cfg["lookback_bars"])
        if anchor_cfg.get("lookback_bars") is not None
        else None,
        one_shot=bool(params.get("one_shot", True)),
    )
    try:
        return StopLossRule(
            field_price=field_price,
            loss_pct=float(loss_pct),
            fraction=float(fraction),
            anchor_config=anchor_config,
            logger=logger,
        )
    except (ValueError, TypeError) as e:
        logger.error(f"stop_loss rule params must be numeric where required: {e}")
        return None


def _create_rule_from_config(rule_name: str, params: dict[str, Any], logger=None):
    """Create a position rule instance from configuration.

    Args:
        rule_name: Name of the rule type ('scaling', 'take_profit', 'stop_loss').
        params: Dictionary of rule-specific parameters.
        logger: Optional logger instance.

    Returns:
        Rule instance if successful, None otherwise.
    """
    # Handle built-in rule types
    builtin_rules = {
        "scaling": _build_scaling_rule,
        "take_profit": _build_take_profit_rule,
        "stop_loss": _build_stop_loss_rule,
    }
    if rule_name in builtin_rules:
        return builtin_rules[rule_name](params, logger)

    # Try to find rule in registry
    registry = get_position_rule_registry()
    rule_class = registry.get_rule_class(rule_name)
    if rule_class is None:
        logger.error(f"Unknown rule type: {rule_name}")
        return None

    # Try from_config method first
    from_config = getattr(rule_class, "from_config", None)
    if callable(from_config):
        result = from_config(params, logger=logger)
        if result is None:
            logger.error(f"Failed to create rule '{rule_name}' from config")
        return result

    # Fall back to direct instantiation
    try:
        return rule_class(**params, logger=logger)
    except Exception as e:
        logger.error(f"Failed to create rule '{rule_name}': {e}")
        return None


def _load_pipeline_from_file(
    config_file: Path, config_name: str, logger
) -> PositionRulePipeline | None:
    """Load and parse a position manager config file into a pipeline.

    Args:
        config_file: Path to the config file.
        config_name: Original config name for error messages.
        logger: Logger instance.

    Returns:
        PositionRulePipeline instance if successful, None otherwise.
    """
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

    rules_list = config_dict.get("rules", [])
    if not isinstance(rules_list, list):
        logger.error(f"Position manager config 'rules' must be a list, got {type(rules_list)}")
        return None

    rule_instances = []

    for idx, rule_item in enumerate(rules_list):
        if not isinstance(rule_item, dict):
            logger.error(f"Rule at index {idx} must be a dictionary")
            continue

        if len(rule_item) != 1:
            logger.error(f"Rule at index {idx} must have exactly one key (rule name)")
            continue

        rule_name = next(iter(rule_item.keys()))
        params = rule_item[rule_name]

        if not isinstance(params, dict):
            logger.error(f"Rule '{rule_name}' params must be a dictionary")
            continue

        rule_instance = _create_rule_from_config(rule_name, params, logger)
        if rule_instance is not None:
            rule_instances.append(rule_instance)

    if not rule_instances:
        logger.warning(f"No valid rules loaded from {config_file}")
        return None

    pipeline = PositionRulePipeline(rule_instances, logger)
    logger.info(f"Loaded {len(rule_instances)} rule(s) from {config_file}")
    return pipeline


def load_position_manager_config(
    config_name: str | None, logger=None
) -> PositionRulePipeline | None:
    """Load a position manager configuration and create a rule pipeline.

    Args:
        config_name: Name of the config file (without .yaml) or explicit path.
        logger: Optional logger instance.

    Returns:
        PositionRulePipeline instance if successful, None otherwise.
    """
    if config_name is None:
        return None

    logger = logger or get_logger("PositionManagerConfigLoader")

    try:
        config_file = _resolve_config_path(config_name)
        return _load_pipeline_from_file(config_file, config_name, logger)
    except Exception as e:
        logger.error(f"Failed to load position manager config: {e}", exc_info=True)
        return None


def load_position_manager_config_dict(
    config_name: str | None, logger=None
) -> dict[str, Any] | None:
    """Load a position manager configuration as a raw dictionary.

    Args:
        config_name: Name of the config file (without .yaml) or explicit path.
        logger: Optional logger instance.

    Returns:
        Configuration dictionary if successful, None otherwise.
    """
    if config_name is None:
        return None

    logger = logger or get_logger("PositionManagerConfigLoader")

    try:
        config_file = _resolve_config_path(config_name)
        if not config_file.exists():
            return None

        with open(config_file, encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

        if not isinstance(config_dict, dict):
            return None

        return config_dict

    except Exception as e:
        logger.error(f"Failed to load position manager config dict: {e}", exc_info=True)
        return None
