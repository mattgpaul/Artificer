"""Portfolio manager configuration loader.

This module provides functionality to load portfolio manager configurations
from YAML files and construct PortfolioRulePipeline instances.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from infrastructure.logging.logger import get_logger
from system.algo_trader.domain.strategy.portfolio_manager.rules.base import PortfolioRulePipeline
from system.algo_trader.domain.strategy.portfolio_manager.rules.fractional_position_size import (
    FractionalPositionSizeRule,
)
from system.algo_trader.domain.strategy.portfolio_manager.rules.max_capital_deployed import (
    MaxCapitalDeployedRule,
)
from system.algo_trader.domain.strategy.portfolio_manager.rules.registry import (
    get_registry as get_portfolio_rule_registry,
)


def _resolve_config_path(config_name: str) -> Path:
    candidate = Path(config_name)
    if candidate.suffix in {".yaml", ".yml"} or any(sep in config_name for sep in ("/", "\\")):
        return candidate

    base_dir = Path(__file__).resolve().parent
    strategies_dir = base_dir / "strategies"
    return strategies_dir / f"{config_name}.yaml"


def _build_max_capital_deployed_rule(params: dict[str, Any], logger=None):
    max_deployed_pct = params.get("max_deployed_pct", 0.5)
    try:
        return MaxCapitalDeployedRule(max_deployed_pct=float(max_deployed_pct), logger=logger)
    except (ValueError, TypeError) as e:
        logger.error(f"max_capital_deployed rule params must be numeric: {e}")
        return None


def _build_fractional_position_size_rule(params: dict[str, Any], logger=None):
    fraction = params.get("fraction_of_equity", 0.01)
    try:
        return FractionalPositionSizeRule(
            fraction_of_equity=float(fraction),
            logger=logger,
        )
    except (ValueError, TypeError) as e:
        logger.error(f"fractional_position_size rule params must be numeric: {e}")
        return None


def _create_rule_from_config(rule_name: str, params: dict[str, Any], logger=None):
    if rule_name == "max_capital_deployed":
        return _build_max_capital_deployed_rule(params, logger)
    if rule_name == "fractional_position_size":
        return _build_fractional_position_size_rule(params, logger)

    registry = get_portfolio_rule_registry()
    rule_class = registry.get_rule_class(rule_name)
    if rule_class is not None:
        from_config = getattr(rule_class, "from_config", None)
        if callable(from_config):
            result = from_config(params, logger=logger)
            if result is None:
                logger.error(f"Failed to create portfolio rule '{rule_name}' from config")
            return result
        try:
            return rule_class(**params, logger=logger)
        except Exception as e:
            logger.error(f"Failed to create portfolio rule '{rule_name}': {e}")
            return None

    logger.error(f"Unknown rule type: {rule_name}")
    return None


def _load_pipeline_from_file(
    config_file: Path, config_name: str, logger
) -> PortfolioRulePipeline | None:
    if not config_file.exists():
        logger.error(
            "Portfolio manager config file not found: "
            f"{config_file} (from '{config_name}'). "
            "Expected a file under 'strategy/portfolio_manager/strategies' "
            "or a valid explicit path."
        )
        return None

    with open(config_file, encoding="utf-8") as f:
        config_dict = yaml.safe_load(f) or {}

    if not isinstance(config_dict, dict):
        logger.error(f"Portfolio manager config must be a dictionary, got {type(config_dict)}")
        return None

    rules_list = config_dict.get("rules", [])
    if not isinstance(rules_list, list):
        logger.error(f"Portfolio manager config 'rules' must be a list, got {type(rules_list)}")
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

    pipeline = PortfolioRulePipeline(rule_instances, logger)
    logger.info(f"Loaded {len(rule_instances)} rule(s) from {config_file}")
    return pipeline


def load_portfolio_manager_config(
    config_name: str | None, logger=None
) -> PortfolioRulePipeline | None:
    """Load portfolio manager configuration from YAML file.

    Args:
        config_name: Configuration name or path to YAML file.
        logger: Optional logger instance.

    Returns:
        PortfolioRulePipeline instance if successful, None otherwise.
    """
    if config_name is None:
        return None

    logger = logger or get_logger("PortfolioManagerConfigLoader")

    try:
        config_file = _resolve_config_path(config_name)
        return _load_pipeline_from_file(config_file, config_name, logger)
    except Exception as e:
        logger.error(f"Failed to load portfolio manager config: {e}", exc_info=True)
        return None
