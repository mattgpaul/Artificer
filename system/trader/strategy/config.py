# Simple strategy configuration manager
_strategy_configs = {}

def set_config(strategy_name: str, config: dict):
    """Set configuration for a strategy"""
    _strategy_configs[strategy_name] = config

def get_config(strategy_name: str, defaults: dict = None) -> dict:
    """Get configuration for a strategy, with optional defaults"""
    return _strategy_configs.get(strategy_name, defaults or {})

def get_function_config(strategy_name: str, function_name: str, defaults: dict = None) -> dict:
    """Get configuration for a specific function within a strategy"""
    strategy_config = get_config(strategy_name, {})
    return strategy_config.get(function_name, defaults or {})
