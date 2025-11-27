"""Position rule registry for discovering and managing position rules.

This module provides a registry system that automatically discovers position rule
classes from the position_manager.rules package and provides access to them by rule type.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any


class PositionRuleRegistry:
    """Registry for discovering and managing position rule classes.

    Automatically discovers position rule classes from the position_manager.rules
    package by inspecting classes that have a `rule_type` class variable. Provides
    methods to retrieve rule classes by type and list all available rule types.
    """

    def __init__(self) -> None:
        """Initialize the position rule registry and discover available rules."""
        self._rules: dict[str, type[Any]] = {}
        self._discover_rules()

    def _discover_rules(self) -> None:
        """Discover all position rule classes from the rules package."""
        package_name = "system.algo_trader.strategy.position_manager.rules"
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return

        for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ != module.__name__:
                    continue
                rule_type = getattr(obj, "rule_type", None)
                if isinstance(rule_type, str) and rule_type:
                    self._rules[rule_type] = obj

    def get_rule_class(self, rule_type: str) -> type[Any] | None:
        """Get a position rule class by its rule type.

        Args:
            rule_type: The rule type identifier (e.g., "stop_loss").

        Returns:
            The rule class if found, None otherwise.
        """
        return self._rules.get(rule_type)

    def get_all_rule_types(self) -> list[str]:
        """Get all registered position rule types.

        Returns:
            A sorted list of all available rule type identifiers.
        """
        return sorted(self._rules.keys())


_registry: PositionRuleRegistry | None = None


def get_registry() -> PositionRuleRegistry:
    """Get or create the singleton position rule registry instance.

    Returns:
        The global PositionRuleRegistry instance.
    """
    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = PositionRuleRegistry()
    return _registry
