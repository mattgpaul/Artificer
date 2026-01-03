"""Unit tests for Timescale Enums - FrequencyType and PeriodType.

Tests cover validation logic for frequency types, period types, and their valid combinations
for Schwab API price history requests.
"""

import pytest

from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class TestFrequencyType:
    """Test FrequencyType enum and validation."""

    def test_frequency_type_values(self):
        """Test that all frequency types have correct string values."""
        assert FrequencyType.MINUTE.value == "minute"
        assert FrequencyType.DAILY.value == "daily"
        assert FrequencyType.WEEKLY.value == "weekly"
        assert FrequencyType.MONTHLY.value == "monthly"

    def test_minute_valid_frequencies(self):
        """Test valid frequency values for MINUTE type."""
        assert FrequencyType.MINUTE.is_valid_frequency(1) is True
        assert FrequencyType.MINUTE.is_valid_frequency(5) is True
        assert FrequencyType.MINUTE.is_valid_frequency(10) is True
        assert FrequencyType.MINUTE.is_valid_frequency(15) is True
        assert FrequencyType.MINUTE.is_valid_frequency(30) is True

    def test_minute_invalid_frequencies(self):
        """Test invalid frequency values for MINUTE type."""
        assert FrequencyType.MINUTE.is_valid_frequency(2) is False
        assert FrequencyType.MINUTE.is_valid_frequency(7) is False
        assert FrequencyType.MINUTE.is_valid_frequency(60) is False
        assert FrequencyType.MINUTE.is_valid_frequency(100) is False

    def test_daily_valid_frequency(self):
        """Test valid frequency values for DAILY type."""
        assert FrequencyType.DAILY.is_valid_frequency(1) is True

    def test_daily_invalid_frequencies(self):
        """Test invalid frequency values for DAILY type."""
        assert FrequencyType.DAILY.is_valid_frequency(2) is False
        assert FrequencyType.DAILY.is_valid_frequency(5) is False
        assert FrequencyType.DAILY.is_valid_frequency(10) is False

    def test_weekly_valid_frequency(self):
        """Test valid frequency values for WEEKLY type."""
        assert FrequencyType.WEEKLY.is_valid_frequency(1) is True

    def test_weekly_invalid_frequencies(self):
        """Test invalid frequency values for WEEKLY type."""
        assert FrequencyType.WEEKLY.is_valid_frequency(2) is False
        assert FrequencyType.WEEKLY.is_valid_frequency(4) is False

    def test_monthly_valid_frequency(self):
        """Test valid frequency values for MONTHLY type."""
        assert FrequencyType.MONTHLY.is_valid_frequency(1) is True

    def test_monthly_invalid_frequencies(self):
        """Test invalid frequency values for MONTHLY type."""
        assert FrequencyType.MONTHLY.is_valid_frequency(3) is False
        assert FrequencyType.MONTHLY.is_valid_frequency(6) is False


class TestPeriodType:
    """Test PeriodType enum and validation."""

    def test_period_type_values(self):
        """Test that all period types have correct string values."""
        assert PeriodType.DAY.value == "day"
        assert PeriodType.MONTH.value == "month"
        assert PeriodType.YEAR.value == "year"
        assert PeriodType.YTD.value == "ytd"

    def test_day_valid_periods(self):
        """Test valid period values for DAY type."""
        for period in [1, 2, 3, 4, 5, 10]:
            PeriodType.DAY.validate_combination(period, FrequencyType.MINUTE, 1)

    def test_day_invalid_periods(self):
        """Test invalid period values for DAY type."""
        with pytest.raises(ValueError, match="Invalid period"):
            PeriodType.DAY.validate_combination(6, FrequencyType.MINUTE, 1)
        with pytest.raises(ValueError, match="Invalid period"):
            PeriodType.DAY.validate_combination(15, FrequencyType.MINUTE, 1)

    def test_month_valid_periods(self):
        """Test valid period values for MONTH type."""
        for period in [1, 2, 3, 6, 12]:
            PeriodType.MONTH.validate_combination(period, FrequencyType.DAILY, 1)

    def test_month_invalid_periods(self):
        """Test invalid period values for MONTH type."""
        with pytest.raises(ValueError, match="Invalid period"):
            PeriodType.MONTH.validate_combination(4, FrequencyType.DAILY, 1)
        with pytest.raises(ValueError, match="Invalid period"):
            PeriodType.MONTH.validate_combination(24, FrequencyType.DAILY, 1)

    def test_year_valid_periods(self):
        """Test valid period values for YEAR type."""
        for period in [1, 2, 3, 5, 10, 15, 20]:
            PeriodType.YEAR.validate_combination(period, FrequencyType.DAILY, 1)

    def test_year_invalid_periods(self):
        """Test invalid period values for YEAR type."""
        with pytest.raises(ValueError, match="Invalid period"):
            PeriodType.YEAR.validate_combination(4, FrequencyType.DAILY, 1)
        with pytest.raises(ValueError, match="Invalid period"):
            PeriodType.YEAR.validate_combination(25, FrequencyType.DAILY, 1)

    def test_ytd_valid_period(self):
        """Test valid period value for YTD type."""
        PeriodType.YTD.validate_combination(1, FrequencyType.DAILY, 1)

    def test_ytd_invalid_period(self):
        """Test invalid period values for YTD type."""
        with pytest.raises(ValueError, match="Invalid period"):
            PeriodType.YTD.validate_combination(2, FrequencyType.DAILY, 1)


class TestPeriodFrequencyCombinations:
    """Test valid and invalid combinations of period and frequency types."""

    def test_day_period_valid_frequency_types(self):
        """Test DAY period only accepts MINUTE frequency type."""
        # Valid: DAY + MINUTE
        PeriodType.DAY.validate_combination(1, FrequencyType.MINUTE, 5)

        # Invalid: DAY + other frequency types
        with pytest.raises(ValueError, match="Invalid frequency type"):
            PeriodType.DAY.validate_combination(1, FrequencyType.DAILY, 1)
        with pytest.raises(ValueError, match="Invalid frequency type"):
            PeriodType.DAY.validate_combination(1, FrequencyType.WEEKLY, 1)
        with pytest.raises(ValueError, match="Invalid frequency type"):
            PeriodType.DAY.validate_combination(1, FrequencyType.MONTHLY, 1)

    def test_month_period_valid_frequency_types(self):
        """Test MONTH period accepts DAILY and WEEKLY frequency types."""
        # Valid: MONTH + DAILY
        PeriodType.MONTH.validate_combination(1, FrequencyType.DAILY, 1)

        # Valid: MONTH + WEEKLY
        PeriodType.MONTH.validate_combination(1, FrequencyType.WEEKLY, 1)

        # Invalid: MONTH + MINUTE
        with pytest.raises(ValueError, match="Invalid frequency type"):
            PeriodType.MONTH.validate_combination(1, FrequencyType.MINUTE, 1)

        # Invalid: MONTH + MONTHLY
        with pytest.raises(ValueError, match="Invalid frequency type"):
            PeriodType.MONTH.validate_combination(1, FrequencyType.MONTHLY, 1)

    def test_year_period_valid_frequency_types(self):
        """Test YEAR period accepts DAILY, WEEKLY, and MONTHLY frequency types."""
        # Valid: YEAR + DAILY
        PeriodType.YEAR.validate_combination(1, FrequencyType.DAILY, 1)

        # Valid: YEAR + WEEKLY
        PeriodType.YEAR.validate_combination(1, FrequencyType.WEEKLY, 1)

        # Valid: YEAR + MONTHLY
        PeriodType.YEAR.validate_combination(1, FrequencyType.MONTHLY, 1)

        # Invalid: YEAR + MINUTE
        with pytest.raises(ValueError, match="Invalid frequency type"):
            PeriodType.YEAR.validate_combination(1, FrequencyType.MINUTE, 1)

    def test_ytd_period_valid_frequency_types(self):
        """Test YTD period accepts DAILY and WEEKLY frequency types."""
        # Valid: YTD + DAILY
        PeriodType.YTD.validate_combination(1, FrequencyType.DAILY, 1)

        # Valid: YTD + WEEKLY
        PeriodType.YTD.validate_combination(1, FrequencyType.WEEKLY, 1)

        # Invalid: YTD + MINUTE
        with pytest.raises(ValueError, match="Invalid frequency type"):
            PeriodType.YTD.validate_combination(1, FrequencyType.MINUTE, 1)

        # Invalid: YTD + MONTHLY
        with pytest.raises(ValueError, match="Invalid frequency type"):
            PeriodType.YTD.validate_combination(1, FrequencyType.MONTHLY, 1)

    def test_invalid_frequency_values(self):
        """Test that invalid frequency values are rejected."""
        # Invalid frequency value for MINUTE
        with pytest.raises(ValueError, match="Invalid frequency"):
            PeriodType.DAY.validate_combination(1, FrequencyType.MINUTE, 7)

        # Invalid frequency value for DAILY
        with pytest.raises(ValueError, match="Invalid frequency"):
            PeriodType.MONTH.validate_combination(1, FrequencyType.DAILY, 2)

        # Invalid frequency value for WEEKLY
        with pytest.raises(ValueError, match="Invalid frequency"):
            PeriodType.MONTH.validate_combination(1, FrequencyType.WEEKLY, 4)


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_intraday_trading_5min_chart(self):
        """Test configuration for 5-minute intraday chart."""
        # 1 day, 5-minute intervals
        PeriodType.DAY.validate_combination(1, FrequencyType.MINUTE, 5)

    def test_weekly_price_action(self):
        """Test configuration for weekly price action over 6 months."""
        # 6 months, weekly intervals
        PeriodType.MONTH.validate_combination(6, FrequencyType.WEEKLY, 1)

    def test_long_term_daily_chart(self):
        """Test configuration for long-term daily chart."""
        # 5 years, daily intervals
        PeriodType.YEAR.validate_combination(5, FrequencyType.DAILY, 1)

    def test_year_to_date_weekly(self):
        """Test configuration for year-to-date weekly chart."""
        # YTD, weekly intervals
        PeriodType.YTD.validate_combination(1, FrequencyType.WEEKLY, 1)

    def test_scalping_1min_chart(self):
        """Test configuration for 1-minute scalping chart."""
        # 1 day, 1-minute intervals
        PeriodType.DAY.validate_combination(1, FrequencyType.MINUTE, 1)

    def test_monthly_candles_multi_year(self):
        """Test configuration for monthly candles over multiple years."""
        # 10 years, monthly intervals
        PeriodType.YEAR.validate_combination(10, FrequencyType.MONTHLY, 1)
