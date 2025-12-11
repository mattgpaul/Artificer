"""Filter registry for discovering and managing strategy filters.

This module provides a registry system that automatically discovers filter classes
from the filters package and provides access to them by filter type.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any


class FilterRegistry:
    """Registry for discovering and managing strategy filter classes.

    Automatically discovers filter classes from the filters package by inspecting
    classes that have a `filter_type` class variable. Provides methods to retrieve
    filter classes by type and list all available filter types.
    """

    def __init__(self) -> None:
        """Initialize the filter registry and discover available filters."""
        self._filters: dict[str, type[Any]] = {}
        self._discover_filters()

    def _discover_filters(self) -> None:
        """Discover all filter classes from the filters package."""
        package_name = "system.algo_trader.strategy.filters"
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return

        for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            if module_name.endswith(".strategies"):
                continue
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ != module.__name__:
                    continue
                filter_type = getattr(obj, "filter_type", None)
                if isinstance(filter_type, str) and filter_type:
                    self._filters[filter_type] = obj

    def get_filter_class(self, filter_type: str) -> type[Any] | None:
        """Get a filter class by its filter type.

        Args:
            filter_type: The filter type identifier (e.g., "price_comparison").

        Returns:
            The filter class if found, None otherwise.
        """
        return self._filters.get(filter_type)

    def get_all_filter_types(self) -> list[str]:
        """Get all registered filter types.

        Returns:
            A sorted list of all available filter type identifiers.
        """
        return sorted(self._filters.keys())


_registry: FilterRegistry | None = None


def get_registry() -> FilterRegistry:
    """Get or create the singleton filter registry instance.

    Returns:
        The global FilterRegistry instance.
    """
    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = FilterRegistry()
    return _registry
