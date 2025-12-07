"""Unit tests for Timescale enums – FrequencyType and PeriodType.

Tests cover:
- Valid/invalid frequency values for each FrequencyType
- Valid/invalid period/frequency combinations for PeriodType.validate_combination
"""

from __future__ import annotations

import pytest

from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


@pytest.mark.unit
class TestFrequencyType:
    """Tests for FrequencyType.is_valid_frequency."""

    @pytest.mark.parametrize(
        "freq",
        [1, 5, 10, 15, 30],
    )
    def test_minute_valid_frequencies(self, freq: int) -> None:
        """MINUTE allows common intraday bar sizes."""
        assert FrequencyType.MINUTE.is_valid_frequency(freq) is True

    @pytest.mark.parametrize(
        "freq",
        [2, 3, 7, 60],
    )
    def test_minute_invalid_frequencies(self, freq: int) -> None:
        """MINUTE rejects unsupported bar sizes."""
        assert FrequencyType.MINUTE.is_valid_frequency(freq) is False

    def test_daily_weekly_monthly_only_allow_1(self) -> None:
        """DAILY, WEEKLY, MONTHLY only accept frequency=1."""
        for freq_type in (FrequencyType.DAILY, FrequencyType.WEEKLY, FrequencyType.MONTHLY):
            assert freq_type.is_valid_frequency(1) is True
            assert freq_type.is_valid_frequency(2) is False


@pytest.mark.unit
class TestPeriodTypeValidateCombination:
    """Tests for PeriodType.validate_combination."""

    @pytest.mark.parametrize(
        "period_type,period,frequency_type,frequency",
        [
            (PeriodType.DAY, 1, FrequencyType.MINUTE, 1),
            (PeriodType.DAY, 5, FrequencyType.MINUTE, 5),
            (PeriodType.MONTH, 1, FrequencyType.DAILY, 1),
            (PeriodType.MONTH, 6, FrequencyType.WEEKLY, 1),
            (PeriodType.YEAR, 1, FrequencyType.DAILY, 1),
            (PeriodType.YEAR, 5, FrequencyType.MONTHLY, 1),
            (PeriodType.YTD, 1, FrequencyType.DAILY, 1),
        ],
    )
    def test_valid_combinations(
        self,
        period_type: PeriodType,
        period: int,
        frequency_type: FrequencyType,
        frequency: int,
    ) -> None:
        """Combinations that match Schwab rules should not raise."""
        period_type.validate_combination(period, frequency_type, frequency)

    @pytest.mark.parametrize(
        "period_type,invalid_period",
        [
            (PeriodType.DAY, 7),
            (PeriodType.MONTH, 4),
            (PeriodType.YEAR, 7),
            (PeriodType.YTD, 2),
        ],
    )
    def test_invalid_period_raises_value_error(
        self,
        period_type: PeriodType,
        invalid_period: int,
    ) -> None:
        """Invalid period values should raise ValueError."""
        with pytest.raises(ValueError):
            period_type.validate_combination(
                invalid_period,
                FrequencyType.DAILY,
                1,
            )

    @pytest.mark.parametrize(
        "period_type,frequency_type",
        [
            (PeriodType.DAY, FrequencyType.DAILY),
            (PeriodType.DAY, FrequencyType.MONTHLY),
            (PeriodType.MONTH, FrequencyType.MINUTE),
            (PeriodType.YEAR, FrequencyType.MINUTE),
            (PeriodType.YTD, FrequencyType.MONTHLY),
        ],
    )
    def test_invalid_frequency_type_raises_value_error(
        self,
        period_type: PeriodType,
        frequency_type: FrequencyType,
    ) -> None:
        """Invalid frequency type for a given period type should raise."""
        with pytest.raises(ValueError):
            period_type.validate_combination(1, frequency_type, 1)

    def test_invalid_frequency_value_raises_value_error(self) -> None:
        """Invalid frequency value for a valid freq type should raise."""
        with pytest.raises(ValueError):
            PeriodType.DAY.validate_combination(
                1,
                FrequencyType.MINUTE,
                2,  # invalid for MINUTE
            )


