"""Price comparison filter implementation.

This module provides a filter that compares a signal field value to a constant threshold.
"""

from __future__ import annotations

from typing import Any, ClassVar

from system.algo_trader.strategy.filters.base import BaseComparisonFilter
from system.algo_trader.strategy.filters.core import FilterContext


class PriceComparisonFilter(BaseComparisonFilter):
    """Filter that compares a signal field value to a constant threshold."""

    filter_type: ClassVar[str] = "price_comparison"

    def __init__(self, field: str, operator: str, value: float, logger=None):
        """Initialize price comparison filter.

        Args:
            field: Name of the signal field to compare.
            operator: Comparison operator (>, <, >=, <=, ==, !=).
            value: Threshold value to compare against.
            logger: Optional logger instance.
        """
        super().__init__(operator, logger)
        self.field = field
        self.value = value

    def evaluate(self, context: FilterContext) -> bool:
        """Evaluate whether the signal field passes the comparison.

        Args:
            context: FilterContext containing signal data.

        Returns:
            True if comparison succeeds, False otherwise.
        """
        signal = context.signal
        field_value = signal.get(self.field)

        if field_value is None:
            self.logger.debug(f"Field {self.field} not found in signal, rejecting")
            return False

        try:
            field_value = float(field_value)
        except (ValueError, TypeError):
            self.logger.debug(
                f"Field {self.field} value {field_value} cannot be converted to float, rejecting"
            )
            return False

        return self._compare_values(field_value, self.value)

    @classmethod
    def from_config(cls, params: dict[str, Any], logger=None) -> "PriceComparisonFilter" | None:
        field = params.get("field")
        operator = params.get("operator")
        value = params.get("value")

        if field is None or operator is None or value is None:
            if logger is not None:
                logger.error(
                    "price_comparison filter missing required params: field, operator, value"
                )
            return None

        try:
            value_float = float(value)
        except (ValueError, TypeError):
            if logger is not None:
                logger.error(f"price_comparison filter value must be numeric, got {value}")
            return None

        return cls(field=field, operator=operator, value=value_float, logger=logger)
