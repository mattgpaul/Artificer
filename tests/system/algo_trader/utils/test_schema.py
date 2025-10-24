"""Unit tests for Schema Models - StockQuote and MarketHours.

Tests cover Pydantic model validation, field types, and timezone handling.
All tests are isolated and don't require external dependencies.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from system.algo_trader.utils.schema import MarketHours, StockQuote


class TestStockQuoteInitialization:
    """Test StockQuote model initialization and validation."""

    def test_valid_stock_quote_creation(self):
        """Test creating a valid StockQuote."""
        quote = StockQuote(
            price=150.25,
            bid=150.20,
            ask=150.30,
            volume=1000000,
            change=2.50,
            change_pct=1.69,
            timestamp=1609459200,
        )

        assert quote.price == 150.25
        assert quote.bid == 150.20
        assert quote.ask == 150.30
        assert quote.volume == 1000000
        assert quote.change == 2.50
        assert quote.change_pct == 1.69
        assert quote.timestamp == 1609459200

    def test_stock_quote_with_dict(self):
        """Test creating StockQuote from dictionary."""
        data = {
            "price": 200.0,
            "bid": 199.95,
            "ask": 200.05,
            "volume": 500000,
            "change": -1.5,
            "change_pct": -0.74,
            "timestamp": 1609545600,
        }

        quote = StockQuote(**data)

        assert quote.price == 200.0
        assert quote.volume == 500000

    def test_stock_quote_with_zero_values(self):
        """Test StockQuote with zero values."""
        quote = StockQuote(
            price=0.0, bid=0.0, ask=0.0, volume=0, change=0.0, change_pct=0.0, timestamp=0
        )

        assert quote.price == 0.0
        assert quote.volume == 0

    def test_stock_quote_negative_change(self):
        """Test StockQuote with negative change values."""
        quote = StockQuote(
            price=100.0,
            bid=99.95,
            ask=100.05,
            volume=1000,
            change=-5.25,
            change_pct=-5.0,
            timestamp=1609459200,
        )

        assert quote.change == -5.25
        assert quote.change_pct == -5.0

    def test_stock_quote_large_volume(self):
        """Test StockQuote with very large volume."""
        quote = StockQuote(
            price=50.0,
            bid=49.99,
            ask=50.01,
            volume=999999999,
            change=1.0,
            change_pct=2.0,
            timestamp=1609459200,
        )

        assert quote.volume == 999999999


class TestStockQuoteValidation:
    """Test StockQuote validation and error handling."""

    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StockQuote(
                price=150.0,
                bid=149.95,
                ask=150.05,
                volume=1000,
                # Missing: change, change_pct, timestamp
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 3  # At least 3 missing fields

    def test_invalid_price_type(self):
        """Test that invalid price type raises ValidationError."""
        with pytest.raises(ValidationError):
            StockQuote(
                price="invalid",  # Should be float
                bid=150.0,
                ask=150.05,
                volume=1000,
                change=1.0,
                change_pct=1.0,
                timestamp=1609459200,
            )

    def test_invalid_volume_type(self):
        """Test that invalid volume type raises ValidationError."""
        with pytest.raises(ValidationError):
            StockQuote(
                price=150.0,
                bid=150.0,
                ask=150.05,
                volume="not_an_int",  # Should be int
                change=1.0,
                change_pct=1.0,
                timestamp=1609459200,
            )

    def test_volume_float_with_fractional_part_raises_error(self):
        """Test that float volume with fractional part raises ValidationError."""
        # Pydantic v2 doesn't coerce floats with fractional parts to int
        with pytest.raises(ValidationError):
            StockQuote(
                price=150.0,
                bid=150.0,
                ask=150.05,
                volume=1000.5,  # Float with fractional part - not allowed
                change=1.0,
                change_pct=1.0,
                timestamp=1609459200,
            )

    def test_timestamp_float_with_fractional_part_raises_error(self):
        """Test that float timestamp with fractional part raises ValidationError."""
        # Pydantic v2 doesn't coerce floats with fractional parts to int
        with pytest.raises(ValidationError):
            StockQuote(
                price=150.0,
                bid=150.0,
                ask=150.05,
                volume=1000,
                change=1.0,
                change_pct=1.0,
                timestamp=1609459200.5,  # Float with fractional part - not allowed
            )

    def test_string_numeric_coercion(self):
        """Test that numeric strings are coerced to correct types."""
        quote = StockQuote(
            price="150.25",
            bid="150.20",
            ask="150.30",
            volume="1000",
            change="2.5",
            change_pct="1.69",
            timestamp="1609459200",
        )

        assert quote.price == 150.25
        assert quote.volume == 1000
        assert isinstance(quote.price, float)
        assert isinstance(quote.volume, int)


class TestStockQuoteSerialization:
    """Test StockQuote serialization and deserialization."""

    def test_model_dump(self):
        """Test converting StockQuote to dictionary."""
        quote = StockQuote(
            price=150.0,
            bid=149.95,
            ask=150.05,
            volume=1000000,
            change=2.5,
            change_pct=1.69,
            timestamp=1609459200,
        )

        data = quote.model_dump()

        assert isinstance(data, dict)
        assert data["price"] == 150.0
        assert data["volume"] == 1000000
        assert len(data) == 7

    def test_model_dump_json(self):
        """Test converting StockQuote to JSON."""
        quote = StockQuote(
            price=150.0,
            bid=149.95,
            ask=150.05,
            volume=1000000,
            change=2.5,
            change_pct=1.69,
            timestamp=1609459200,
        )

        json_str = quote.model_dump_json()

        assert isinstance(json_str, str)
        assert "150.0" in json_str
        assert "1000000" in json_str

    def test_round_trip_serialization(self):
        """Test serializing and deserializing StockQuote."""
        original = StockQuote(
            price=123.45,
            bid=123.40,
            ask=123.50,
            volume=5000000,
            change=-2.15,
            change_pct=-1.71,
            timestamp=1609459200,
        )

        # Convert to dict and back
        data = original.model_dump()
        restored = StockQuote(**data)

        assert restored.price == original.price
        assert restored.volume == original.volume
        assert restored.timestamp == original.timestamp


class TestMarketHoursInitialization:
    """Test MarketHours model initialization."""

    def test_market_hours_with_utc_datetimes(self):
        """Test creating MarketHours with UTC datetimes."""
        date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        start = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)  # 9:30 AM EST
        end = datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc)  # 4:00 PM EST

        hours = MarketHours(date=date, start=start, end=end)

        assert hours.date == date
        assert hours.start == start
        assert hours.end == end
        assert hours.start.tzinfo == timezone.utc
        assert hours.end.tzinfo == timezone.utc

    def test_market_hours_with_est_datetimes(self):
        """Test creating MarketHours with EST datetimes (auto-converts to UTC)."""
        est = ZoneInfo("America/New_York")
        date = datetime(2024, 1, 15, tzinfo=est)
        start = datetime(2024, 1, 15, 9, 30, tzinfo=est)  # 9:30 AM EST
        end = datetime(2024, 1, 15, 16, 0, tzinfo=est)  # 4:00 PM EST

        hours = MarketHours(date=date, start=start, end=end)

        # Should be converted to UTC
        assert hours.start.tzinfo == timezone.utc
        assert hours.end.tzinfo == timezone.utc
        # Verify conversion is correct (EST is UTC-5)
        assert hours.start.hour == 14  # 9:30 AM EST = 2:30 PM UTC
        assert hours.end.hour == 21  # 4:00 PM EST = 9:00 PM UTC

    def test_market_hours_with_naive_datetimes(self):
        """Test creating MarketHours with naive datetimes (assumes EST)."""
        date = datetime(2024, 1, 15)
        start = datetime(2024, 1, 15, 9, 30)  # Naive - will be treated as EST
        end = datetime(2024, 1, 15, 16, 0)  # Naive - will be treated as EST

        hours = MarketHours(date=date, start=start, end=end)

        # Should be converted to UTC (assumes EST/EDT based on date)
        assert hours.start.tzinfo == timezone.utc
        assert hours.end.tzinfo == timezone.utc

    def test_market_hours_with_dict(self):
        """Test creating MarketHours from dictionary."""
        data = {
            "date": datetime(2024, 1, 15, tzinfo=timezone.utc),
            "start": datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
            "end": datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc),
        }

        hours = MarketHours(**data)

        assert hours.date == data["date"]
        assert hours.start == data["start"]
        assert hours.end == data["end"]


class TestMarketHoursTimezoneConversion:
    """Test MarketHours timezone conversion validator."""

    def test_timezone_conversion_est_to_utc(self):
        """Test explicit EST to UTC conversion."""
        est = ZoneInfo("America/New_York")
        # January date - EST (not EDT)
        start_est = datetime(2024, 1, 15, 9, 30, tzinfo=est)
        end_est = datetime(2024, 1, 15, 16, 0, tzinfo=est)

        hours = MarketHours(date=datetime(2024, 1, 15, tzinfo=est), start=start_est, end=end_est)

        # Verify conversion to UTC
        assert hours.start.tzinfo == timezone.utc
        assert hours.end.tzinfo == timezone.utc

    def test_timezone_conversion_edt_to_utc(self):
        """Test EDT (daylight saving) to UTC conversion."""
        est = ZoneInfo("America/New_York")
        # July date - EDT (UTC-4)
        start_edt = datetime(2024, 7, 15, 9, 30, tzinfo=est)
        end_edt = datetime(2024, 7, 15, 16, 0, tzinfo=est)

        hours = MarketHours(date=datetime(2024, 7, 15, tzinfo=est), start=start_edt, end=end_edt)

        # EDT is UTC-4, so 9:30 EDT = 13:30 UTC
        assert hours.start.tzinfo == timezone.utc
        assert hours.start.hour == 13  # 9:30 AM EDT = 1:30 PM UTC
        assert hours.end.hour == 20  # 4:00 PM EDT = 8:00 PM UTC

    def test_timezone_conversion_pst_to_utc(self):
        """Test PST to UTC conversion."""
        pst = ZoneInfo("America/Los_Angeles")
        start_pst = datetime(2024, 1, 15, 6, 30, tzinfo=pst)  # 6:30 AM PST
        end_pst = datetime(2024, 1, 15, 13, 0, tzinfo=pst)  # 1:00 PM PST

        hours = MarketHours(date=datetime(2024, 1, 15, tzinfo=pst), start=start_pst, end=end_pst)

        # PST is UTC-8, so 6:30 PST = 14:30 UTC
        assert hours.start.tzinfo == timezone.utc
        assert hours.start.hour == 14

    def test_naive_datetime_assumes_est(self):
        """Test that naive datetimes are treated as EST."""
        # Create naive datetime (January - EST period)
        start_naive = datetime(2024, 1, 15, 9, 30)

        hours = MarketHours(
            date=datetime(2024, 1, 15), start=start_naive, end=datetime(2024, 1, 15, 16, 0)
        )

        # Should be converted to UTC
        assert hours.start.tzinfo == timezone.utc
        # EST is UTC-5, so 9:30 EST = 14:30 UTC
        assert hours.start.hour == 14

    def test_already_utc_datetime_unchanged(self):
        """Test that UTC datetimes remain unchanged."""
        start_utc = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        end_utc = datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc)

        hours = MarketHours(
            date=datetime(2024, 1, 15, tzinfo=timezone.utc), start=start_utc, end=end_utc
        )

        # Should remain as UTC
        assert hours.start == start_utc
        assert hours.end == end_utc
        assert hours.start.hour == 14


class TestMarketHoursValidation:
    """Test MarketHours validation and error handling."""

    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MarketHours(
                date=datetime(2024, 1, 15),
                start=datetime(2024, 1, 15, 9, 30),
                # Missing: end
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 1

    def test_string_date_coercion(self):
        """Test that string dates are coerced to datetime by Pydantic."""
        # Pydantic v2 can parse ISO format strings to datetime
        hours = MarketHours(
            date="2024-01-15T00:00:00Z",  # ISO format string - will be parsed
            start=datetime(2024, 1, 15, 9, 30),
            end=datetime(2024, 1, 15, 16, 0),
        )

        assert isinstance(hours.date, datetime)

    def test_invalid_start_type(self):
        """Test that invalid start type raises ValidationError."""
        with pytest.raises(ValidationError):
            MarketHours(
                date=datetime(2024, 1, 15),
                start="09:30:00",  # Should be datetime
                end=datetime(2024, 1, 15, 16, 0),
            )

    def test_all_fields_required(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            MarketHours()


class TestMarketHoursSerialization:
    """Test MarketHours serialization and deserialization."""

    def test_model_dump(self):
        """Test converting MarketHours to dictionary."""
        date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        start = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc)

        hours = MarketHours(date=date, start=start, end=end)
        data = hours.model_dump()

        assert isinstance(data, dict)
        assert "date" in data
        assert "start" in data
        assert "end" in data
        assert len(data) == 3

    def test_model_dump_json(self):
        """Test converting MarketHours to JSON."""
        hours = MarketHours(
            date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            start=datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
            end=datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc),
        )

        json_str = hours.model_dump_json()

        assert isinstance(json_str, str)
        assert "2024" in json_str

    def test_round_trip_serialization_with_timezone(self):
        """Test serializing and deserializing MarketHours preserves timezone."""
        est = ZoneInfo("America/New_York")
        original = MarketHours(
            date=datetime(2024, 1, 15, tzinfo=est),
            start=datetime(2024, 1, 15, 9, 30, tzinfo=est),
            end=datetime(2024, 1, 15, 16, 0, tzinfo=est),
        )

        # Verify conversion happened
        assert original.start.tzinfo == timezone.utc

        # Convert to dict and back
        data = original.model_dump()
        restored = MarketHours(**data)

        assert restored.start == original.start
        assert restored.end == original.end
        assert restored.start.tzinfo == timezone.utc


class TestSchemaIntegration:
    """Test integration scenarios with both models."""

    def test_stock_quote_with_market_hours(self):
        """Test using StockQuote with MarketHours in a typical workflow."""
        # Create market hours
        est = ZoneInfo("America/New_York")
        hours = MarketHours(
            date=datetime(2024, 1, 15, tzinfo=est),
            start=datetime(2024, 1, 15, 9, 30, tzinfo=est),
            end=datetime(2024, 1, 15, 16, 0, tzinfo=est),
        )

        # Create quote during market hours
        quote = StockQuote(
            price=150.0,
            bid=149.95,
            ask=150.05,
            volume=1000000,
            change=2.5,
            change_pct=1.69,
            timestamp=int(hours.start.timestamp()),  # Quote at market open
        )

        assert quote.timestamp > 0
        assert hours.start.tzinfo == timezone.utc

    def test_multiple_quotes_within_market_hours(self):
        """Test multiple quotes during market session."""
        hours = MarketHours(
            date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            start=datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
            end=datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc),
        )

        # Create quotes at different times
        quotes = [
            StockQuote(
                price=150.0 + i,
                bid=149.95 + i,
                ask=150.05 + i,
                volume=1000000 + i * 1000,
                change=i * 0.5,
                change_pct=i * 0.33,
                timestamp=int(hours.start.timestamp()) + i * 3600,
            )
            for i in range(5)
        ]

        assert len(quotes) == 5
        assert all(isinstance(q, StockQuote) for q in quotes)


class TestSchemaEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_stock_quote_with_very_small_values(self):
        """Test StockQuote with very small decimal values."""
        quote = StockQuote(
            price=0.0001,
            bid=0.00009,
            ask=0.00011,
            volume=1,
            change=0.00001,
            change_pct=0.01,
            timestamp=1,
        )

        assert quote.price == 0.0001

    def test_stock_quote_with_very_large_values(self):
        """Test StockQuote with very large values."""
        quote = StockQuote(
            price=999999.99,
            bid=999999.98,
            ask=999999.99,
            volume=999999999,
            change=50000.0,
            change_pct=100.0,
            timestamp=9999999999,
        )

        assert quote.price == 999999.99
        assert quote.volume == 999999999

    def test_market_hours_midnight_times(self):
        """Test MarketHours with midnight times."""
        hours = MarketHours(
            date=datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc),
            start=datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc),
            end=datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc),
        )

        assert hours.start.hour == 0
        assert hours.end.hour == 23

    def test_market_hours_same_start_end(self):
        """Test MarketHours with same start and end time."""
        time = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        hours = MarketHours(date=time, start=time, end=time)

        assert hours.start == hours.end

    def test_stock_quote_extreme_percentage_changes(self):
        """Test StockQuote with extreme percentage changes."""
        # Stock that doubled
        quote_up = StockQuote(
            price=200.0,
            bid=199.95,
            ask=200.05,
            volume=10000000,
            change=100.0,
            change_pct=100.0,
            timestamp=1609459200,
        )

        # Stock that lost 90%
        quote_down = StockQuote(
            price=10.0,
            bid=9.95,
            ask=10.05,
            volume=50000000,
            change=-90.0,
            change_pct=-90.0,
            timestamp=1609459200,
        )

        assert quote_up.change_pct == 100.0
        assert quote_down.change_pct == -90.0

    def test_timezone_edge_case_daylight_saving_transition(self):
        """Test MarketHours around daylight saving time transition."""
        est = ZoneInfo("America/New_York")

        # Day before DST starts (2024 DST starts March 10, 2:00 AM)
        before_dst = MarketHours(
            date=datetime(2024, 3, 9, tzinfo=est),
            start=datetime(2024, 3, 9, 9, 30, tzinfo=est),  # EST
            end=datetime(2024, 3, 9, 16, 0, tzinfo=est),
        )

        # Day after DST starts
        after_dst = MarketHours(
            date=datetime(2024, 3, 11, tzinfo=est),
            start=datetime(2024, 3, 11, 9, 30, tzinfo=est),  # EDT
            end=datetime(2024, 3, 11, 16, 0, tzinfo=est),
        )

        # Both should be in UTC, but EDT start time should be different
        assert before_dst.start.tzinfo == timezone.utc
        assert after_dst.start.tzinfo == timezone.utc
        # EDT is one hour closer to UTC than EST
        assert after_dst.start.hour == before_dst.start.hour - 1
