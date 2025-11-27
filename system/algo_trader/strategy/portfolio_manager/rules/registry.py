from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any


class PortfolioRuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, type[Any]] = {}
        self._discover_rules()

    def _discover_rules(self) -> None:
        package_name = "system.algo_trader.strategy.portfolio_manager.rules"
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return

        for _, module_name, _ in pkgutil.iter_modules(
            package.__path__, package.__name__ + "."
        ):
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
        return self._rules.get(rule_type)

    def get_all_rule_types(self) -> list[str]:
        return sorted(self._rules.keys())


_registry: PortfolioRuleRegistry | None = None


def get_registry() -> PortfolioRuleRegistry:
    global _registry
    if _registry is None:
        _registry = PortfolioRuleRegistry()
    return _registry


