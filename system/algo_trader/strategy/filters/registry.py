from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any


class FilterRegistry:
    def __init__(self) -> None:
        self._filters: dict[str, type[Any]] = {}
        self._discover_filters()

    def _discover_filters(self) -> None:
        package_name = "system.algo_trader.strategy.filters"
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return

        for _, module_name, _ in pkgutil.iter_modules(
            package.__path__, package.__name__ + "."
        ):
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
        return self._filters.get(filter_type)

    def get_all_filter_types(self) -> list[str]:
        return sorted(self._filters.keys())


_registry: FilterRegistry | None = None


def get_registry() -> FilterRegistry:
    global _registry
    if _registry is None:
        _registry = FilterRegistry()
    return _registry


