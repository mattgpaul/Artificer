"""Timescale enumerations for Schwab API price history requests.

This module provides FrequencyType and PeriodType enums with validation
logic for constructing valid price history API requests.
"""

from enum import Enum


class FrequencyType(Enum):
    """Frequency types for Schwab price history API requests.

    Defines valid frequency types (minute, daily, weekly, monthly) and
    validates frequency values for each type per Schwab API requirements.
    """

    MINUTE = "minute"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

    def is_valid_frequency(self, frequency: int) -> bool:
        """Check if frequency value is valid for this frequency type."""
        valid_frequencies = {
            FrequencyType.MINUTE: frozenset([1, 5, 10, 15, 30]),
            FrequencyType.DAILY: frozenset([1]),
            FrequencyType.WEEKLY: frozenset([1]),
            FrequencyType.MONTHLY: frozenset([1]),
        }
        return frequency in valid_frequencies[self]


class PeriodType(Enum):
    """Period types for Schwab price history API requests.

    Defines valid period types (day, month, year, ytd) and validates
    period/frequency combinations per Schwab API requirements.
    """

    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    YTD = "ytd"

    def validate_combination(
        self, period: int, frequency_type: FrequencyType, frequency: int
    ) -> None:
        """Validate entire period/frequency combination - raises ValueError if invalid."""
        # Check period
        valid_periods = {
            PeriodType.DAY: frozenset([1, 2, 3, 4, 5, 10]),
            PeriodType.MONTH: frozenset([1, 2, 3, 6, 12]),
            PeriodType.YEAR: frozenset([1, 2, 3, 5, 10, 15, 20]),
            PeriodType.YTD: frozenset([1]),
        }[self]

        if period not in valid_periods:
            raise ValueError(f"Invalid period {period} for {self.value}")

        # Check frequency type
        valid_freq_types = {
            PeriodType.DAY: frozenset([FrequencyType.MINUTE]),
            PeriodType.MONTH: frozenset([FrequencyType.DAILY, FrequencyType.WEEKLY]),
            PeriodType.YEAR: frozenset(
                [FrequencyType.DAILY, FrequencyType.WEEKLY, FrequencyType.MONTHLY]
            ),
            PeriodType.YTD: frozenset([FrequencyType.DAILY, FrequencyType.WEEKLY]),
        }[self]

        if frequency_type not in valid_freq_types:
            raise ValueError(f"Invalid frequency type {frequency_type.value} for {self.value}")

        # Check frequency value
        if not frequency_type.is_valid_frequency(frequency):
            raise ValueError(f"Invalid frequency {frequency} for {frequency_type.value}")
