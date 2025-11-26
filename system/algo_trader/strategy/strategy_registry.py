"""Strategy registry for auto-discovery and registration.

This module provides automatic discovery of all Strategy subclasses and
registration for CLI usage. Strategies are automatically discovered from
imported modules, eliminating the need for manual registration.
"""

from __future__ import annotations

import inspect
import re
from typing import Any

from system.algo_trader.strategy.strategy import Strategy


def _class_name_to_cli_name(class_name: str) -> str:
    """Convert a class name to a CLI-friendly name.

    Examples:
        SMACrossover -> sma-crossover
        EMACrossover -> ema-crossover
        MyCustomStrategy -> my-custom-strategy
        RSIStrategy -> rsi-strategy

    Args:
        class_name: The class name to convert.

    Returns:
        CLI-friendly name (kebab-case).
    """
    # Handle acronyms at the start (e.g., SMA, EMA, RSI)
    # Split on transitions from lowercase to uppercase or uppercase to uppercase+lowercase
    # Pattern: insert hyphen before uppercase letter that follows lowercase or another uppercase+lowercase
    name = re.sub(r"([a-z])([A-Z])", r"\1-\2", class_name)
    # Also handle sequences of uppercase followed by lowercase (acronyms)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", name)
    # Convert to lowercase
    return name.lower()


class StrategyRegistry:
    """Registry for auto-discovering and managing trading strategies.

    This registry automatically discovers all Strategy subclasses from
    imported modules and provides methods to create instances and register
    CLI arguments.
    """

    def __init__(self) -> None:
        """Initialize the registry and discover strategies."""
        self._strategies: dict[str, type[Strategy]] = {}
        self._discover_strategies()

    def _discover_strategies(self) -> None:
        """Discover all Strategy subclasses from imported modules.

        This method searches through all imported modules to find classes
        that inherit from Strategy. It registers them using their CLI name
        (derived from class name).

        Strategies are discovered by importing modules from the strategies
        package. To add a new strategy:
        1. Create the strategy class file in strategies/
        2. Add it to system/algo_trader/strategy/BUILD (strategies library)
        3. Import it in this method (or use dynamic discovery)
        """
        import importlib

        # List of strategy modules to import
        # This list should match the strategies in the BUILD file
        strategy_module_names = [
            "system.algo_trader.strategy.strategies.sma_crossover",
            "system.algo_trader.strategy.strategies.ema_crossover",
            # Add new strategies here, or use dynamic discovery below
        ]

        # Import and discover strategies
        for module_name in strategy_module_names:
            try:
                module = importlib.import_module(module_name)
                # Find all Strategy subclasses in this module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, Strategy)
                        and obj is not Strategy
                        and obj.__module__ == module_name
                    ):
                        cli_name = _class_name_to_cli_name(name)
                        self._strategies[cli_name] = obj
            except ImportError:
                # Skip modules that can't be imported (may not be in BUILD)
                continue

    def get_strategy_class(self, cli_name: str) -> type[Strategy] | None:
        """Get a strategy class by its CLI name.

        Args:
            cli_name: CLI name of the strategy (e.g., 'sma-crossover').

        Returns:
            Strategy class if found, None otherwise.
        """
        return self._strategies.get(cli_name)

    def get_all_strategy_names(self) -> list[str]:
        """Get all registered strategy CLI names.

        Returns:
            List of CLI names for all registered strategies.
        """
        return sorted(self._strategies.keys())

    def create_strategy(
        self, cli_name: str, args: Any, logger=None
    ) -> Strategy:
        """Create a strategy instance from CLI arguments.

        Args:
            cli_name: CLI name of the strategy (e.g., 'sma-crossover').
            args: Parsed command-line arguments namespace.
            logger: Optional logger instance.

        Returns:
            Strategy instance.

        Raises:
            ValueError: If strategy type is unknown or creation fails.
        """
        strategy_class = self.get_strategy_class(cli_name)
        if strategy_class is None:
            available = ", ".join(self.get_all_strategy_names())
            raise ValueError(
                f"Unknown strategy: '{cli_name}'. "
                f"Available strategies: {available}"
            )

        # Extract common strategy parameters
        from system.algo_trader.strategy.strategy import Side

        side = Side(getattr(args, "side", "LONG"))
        window = getattr(args, "window", None)

        # Get strategy-specific parameters by inspecting the constructor
        sig = inspect.signature(strategy_class.__init__)
        strategy_params: dict[str, Any] = {"side": side}
        if window is not None:
            strategy_params["window"] = window

        # Extract all other parameters from args that match the constructor
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "side", "window", "extra", "_"):
                continue
            if hasattr(args, param_name):
                strategy_params[param_name] = getattr(args, param_name)

        # Create and return the strategy instance
        try:
            return strategy_class(**strategy_params)
        except Exception as e:
            if logger:
                logger.error(f"Failed to create strategy {cli_name}: {e}")
            raise ValueError(f"Failed to create strategy {cli_name}: {e}") from e

    def register_cli_arguments(
        self, subparsers: Any, parser_factory: Any
    ) -> None:
        """Register CLI arguments for all strategies.

        Args:
            subparsers: ArgumentParser subparsers object.
            parser_factory: Function to create a new parser (typically
                subparsers.add_parser).
        """
        for cli_name, strategy_class in sorted(self._strategies.items()):
            parser = parser_factory(cli_name, help=f"{strategy_class.__name__} strategy")
            strategy_class.add_arguments(parser)

    def create_strategy_from_params(
        self, strategy_type: str, strategy_params: dict[str, Any]
    ) -> Strategy:
        """Create a strategy instance from type name and parameters.

        This method supports both CLI names (e.g., 'sma-crossover') and
        class names (e.g., 'SMACrossover') for backward compatibility.

        Args:
            strategy_type: Strategy type (CLI name or class name).
            strategy_params: Dictionary of strategy parameters.

        Returns:
            Strategy instance.

        Raises:
            ValueError: If strategy type is unknown.
        """
        # Try CLI name first
        strategy_class = self.get_strategy_class(strategy_type)
        if strategy_class is None:
            # Try class name (for backward compatibility)
            for cli_name, cls in self._strategies.items():
                if cls.__name__ == strategy_type:
                    strategy_class = cls
                    break

        if strategy_class is None:
            available = ", ".join(self.get_all_strategy_names())
            raise ValueError(
                f"Unknown strategy type: '{strategy_type}'. "
                f"Available strategies: {available}"
            )

        # Convert side parameter if it's a string
        if "side" in strategy_params:
            from system.algo_trader.strategy.strategy import Side

            side_value = strategy_params["side"]
            if isinstance(side_value, str):
                strategy_params["side"] = Side(side_value)

        # Create and return the strategy instance
        try:
            return strategy_class(**strategy_params)
        except Exception as e:
            raise ValueError(
                f"Failed to create strategy {strategy_type}: {e}"
            ) from e


# Global registry instance
_registry: StrategyRegistry | None = None


def get_registry() -> StrategyRegistry:
    """Get the global strategy registry instance.

    Returns:
        StrategyRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = StrategyRegistry()
    return _registry

