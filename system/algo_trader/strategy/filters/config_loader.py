from pathlib import Path
from typing import Any

import yaml

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.filters.core import Filter, FilterPipeline
from system.algo_trader.strategy.filters.filters import PriceComparisonFilter, SmaComparisonFilter


def _resolve_config_path(config_name: str) -> Path:
    candidate = Path(config_name)
    if candidate.suffix in {".yaml", ".yml"} or any(sep in config_name for sep in ("/", "\\")):
        return candidate

    base_dir = Path(__file__).resolve().parent
    strategies_dir = base_dir / "strategies"
    return strategies_dir / f"{config_name}.yaml"


def _create_filter_from_config(filter_config: dict[str, Any], logger=None) -> Filter | None:
    filter_type = filter_config.get("type")
    if not filter_type:
        logger.error("Filter config missing 'type' field")
        return None

    params = filter_config.get("params", {})

    if filter_type == "price_comparison":
        field = params.get("field")
        operator = params.get("operator")
        value = params.get("value")

        if field is None or operator is None or value is None:
            logger.error(f"price_comparison filter missing required params: field, operator, value")
            return None

        try:
            value = float(value)
        except (ValueError, TypeError):
            logger.error(f"price_comparison filter value must be numeric, got {value}")
            return None

        return PriceComparisonFilter(field=field, operator=operator, value=value, logger=logger)

    elif filter_type == "sma_comparison":
        field_fast = params.get("field_fast")
        field_slow = params.get("field_slow")
        operator = params.get("operator")
        fast_window = params.get("fast_window")
        slow_window = params.get("slow_window")

        if field_fast is None or field_slow is None or operator is None:
            logger.error(f"sma_comparison filter missing required params: field_fast, field_slow, operator")
            return None

        return SmaComparisonFilter(
            field_fast=field_fast,
            field_slow=field_slow,
            operator=operator,
            fast_window=fast_window,
            slow_window=slow_window,
            logger=logger,
        )

    else:
        logger.error(f"Unknown filter type: {filter_type}")
        return None


def load_filter_config(config_name: str | None, logger=None) -> FilterPipeline | None:
    if config_name is None:
        return None

    logger = logger or get_logger("FilterConfigLoader")

    try:
        config_file = _resolve_config_path(config_name)
        if not config_file.exists():
            logger.error(f"Filter config file not found: {config_file} (from '{config_name}')")
            return None

        with open(config_file, encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

        if not isinstance(config_dict, dict):
            logger.error(f"Filter config must be a dictionary, got {type(config_dict)}")
            return None

        filters_list = config_dict.get("filters", [])
        if not isinstance(filters_list, list):
            logger.error(f"Filter config 'filters' must be a list, got {type(filters_list)}")
            return None

        filter_instances = []
        for idx, filter_config in enumerate(filters_list):
            if not isinstance(filter_config, dict):
                logger.error(f"Filter config at index {idx} must be a dictionary")
                continue

            filter_instance = _create_filter_from_config(filter_config, logger)
            if filter_instance is not None:
                filter_instances.append(filter_instance)

        if not filter_instances:
            logger.warning(f"No valid filters loaded from {config_file}")
            return None

        logger.info(f"Loaded {len(filter_instances)} filter(s) from {config_file}")
        return FilterPipeline(filter_instances, logger)

    except Exception as e:
        logger.error(f"Failed to load filter config: {e}", exc_info=True)
        return None


def load_filter_configs(config_names: list[str] | None, logger=None) -> FilterPipeline | None:
    if not config_names:
        return None

    logger = logger or get_logger("FilterConfigLoader")
    all_filters = []

    for config_name in config_names:
        pipeline = load_filter_config(config_name, logger)
        if pipeline is not None:
            all_filters.extend(pipeline.filters)

    if not all_filters:
        return None

    logger.info(f"Combined {len(all_filters)} filter(s) from {len(config_names)} config file(s)")
    return FilterPipeline(all_filters, logger)

