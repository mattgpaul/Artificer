"""Base filter classes for value comparison operations.

This module provides base classes for filters that perform value comparisons
using various operators (>, <, >=, <=, ==, !=).
"""

from typing import ClassVar

from infrastructure.logging.logger import get_logger


class BaseComparisonFilter:
    """Base class for filters that perform value comparisons using operators."""

    VALID_OPERATORS: ClassVar[set[str]] = {">", "<", ">=", "<=", "==", "!="}
    FLOAT_EPSILON: ClassVar[float] = 1e-9

    def __init__(self, operator: str, logger=None):
        """Initialize base comparison filter.

        Args:
            operator: Comparison operator to use (>, <, >=, <=, ==, !=).
            logger: Optional logger instance.
        """
        self.operator = operator
        self.logger = logger or get_logger(self.__class__.__name__)
        self._validate_operator()

    def _validate_operator(self):
        """Validate that the operator is one of the supported comparison operators."""
        if self.operator not in self.VALID_OPERATORS:
            raise ValueError(
                f"Invalid operator: {self.operator}. Must be one of {self.VALID_OPERATORS}"
            )

    def _compare_values(self, left: float, right: float) -> bool:
        """Compare two float values using the configured operator.

        Args:
            left: Left operand for comparison.
            right: Right operand for comparison.

        Returns:
            True if comparison succeeds, False otherwise.
        """
        operator_map = {
            ">": lambda left_val, right_val: left_val > right_val,
            "<": lambda left_val, right_val: left_val < right_val,
            ">=": lambda left_val, right_val: left_val >= right_val,
            "<=": lambda left_val, right_val: left_val <= right_val,
            "==": lambda left_val, right_val: abs(left_val - right_val) < self.FLOAT_EPSILON,
            "!=": lambda left_val, right_val: abs(left_val - right_val) >= self.FLOAT_EPSILON,
        }
        compare_func = operator_map.get(self.operator)
        return compare_func(left, right) if compare_func else False
