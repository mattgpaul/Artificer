"""Unit tests for backtest utility functions.

Tests cover DataFrame to dict conversion, NaN handling, datetime conversion,
and edge cases. All external dependencies are mocked.
"""

import pandas as pd
import pytest

from system.algo_trader.backtest.utils.utils import (
    BACKTEST_METRICS_QUEUE_NAME,
    BACKTEST_REDIS_TTL,
    BACKTEST_TRADES_QUEUE_NAME,
    dataframe_to_dict,
)


class TestConstants:
    """Test utility constants."""

    @pytest.mark.unit
    def test_queue_name_constants(self):
        """Test queue name constants."""
        assert BACKTEST_TRADES_QUEUE_NAME == "backtest_trades_queue"
        assert BACKTEST_METRICS_QUEUE_NAME == "backtest_metrics_queue"
        assert BACKTEST_REDIS_TTL == 3600


class TestDataFrameToDict:
    """Test dataframe_to_dict function."""

    @pytest.mark.unit
    def test_dataframe_to_dict_datetime_index(self):
        """Test conversion with DatetimeIndex."""
        dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"] * 5,
                "price": [100.0] * 5,
            },
            index=dates,
        )

        result = dataframe_to_dict(df)

        assert "datetime" in result
        assert len(result["datetime"]) == 5
        assert isinstance(result["datetime"][0], int)
        assert "ticker" in result
        assert len(result["ticker"]) == 5

    @pytest.mark.unit
    def test_dataframe_to_dict_datetime_column(self):
        """Test conversion with datetime column."""
        df = pd.DataFrame(
            {
                "datetime": pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC"),
                "ticker": ["AAPL"] * 3,
                "price": [100.0] * 3,
            }
        )

        result = dataframe_to_dict(df)

        assert "datetime" in result
        assert len(result["datetime"]) == 3
        assert "datetime" not in result or result.get("datetime") is not None
        assert "ticker" in result

    @pytest.mark.unit
    def test_dataframe_to_dict_exit_time_column(self):
        """Test conversion with exit_time column."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "price": [100.0],
            }
        )

        result = dataframe_to_dict(df)

        assert "datetime" in result
        assert len(result["datetime"]) == 1
        assert "exit_time" in result

    @pytest.mark.unit
    def test_dataframe_to_dict_empty_dataframe(self):
        """Test conversion with empty DataFrame."""
        df = pd.DataFrame()

        result = dataframe_to_dict(df)

        assert isinstance(result, dict)
        assert "datetime" in result
        assert len(result["datetime"]) == 0

    @pytest.mark.unit
    def test_dataframe_to_dict_drops_all_nan_columns(self):
        """Test all-NaN columns are dropped."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "all_nan_col": [None],
            }
        )

        result = dataframe_to_dict(df)

        assert "all_nan_col" not in result
        assert "ticker" in result

    @pytest.mark.unit
    def test_dataframe_to_dict_nan_string_columns(self):
        """Test NaN in string columns converted to empty strings."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "entry_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "optional_str": ["value", None],  # Mix of value and NaN
            }
        )

        result = dataframe_to_dict(df)

        assert "optional_str" in result
        assert result["optional_str"][0] == "value"
        assert result["optional_str"][1] == ""  # NaN converted to empty string

    @pytest.mark.unit
    def test_dataframe_to_dict_nan_numeric_columns(self):
        """Test NaN in numeric columns converted to 0."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "entry_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "optional_num": [100.0, None],  # Mix of value and NaN
            }
        )

        result = dataframe_to_dict(df)

        assert "optional_num" in result
        assert result["optional_num"][0] == 100.0
        assert result["optional_num"][1] == 0  # NaN converted to 0

    @pytest.mark.unit
    def test_dataframe_to_dict_datetime_columns_converted(self):
        """Test datetime columns converted to milliseconds."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
            }
        )

        result = dataframe_to_dict(df)

        assert isinstance(result["entry_time"][0], int)
        assert isinstance(result["exit_time"][0], int)
        # Should be milliseconds since epoch
        assert result["entry_time"][0] > 0
        assert result["exit_time"][0] > result["entry_time"][0]

    @pytest.mark.unit
    def test_dataframe_to_dict_preserves_numeric_values(self):
        """Test numeric values are preserved."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
                "shares": [100],
            }
        )

        result = dataframe_to_dict(df)

        assert result["entry_price"][0] == 100.0
        assert result["exit_price"][0] == 105.0
        assert result["gross_pnl"][0] == 500.0
        assert result["shares"][0] == 100

    @pytest.mark.unit
    def test_dataframe_to_dict_preserves_string_values(self):
        """Test string values are preserved."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "side": ["LONG"],
                "strategy": ["SMACrossoverStrategy"],
            }
        )

        result = dataframe_to_dict(df)

        assert result["ticker"][0] == "AAPL"
        assert result["side"][0] == "LONG"
        assert result["strategy"][0] == "SMACrossoverStrategy"

    @pytest.mark.unit
    def test_dataframe_to_dict_mixed_nan_values(self):
        """Test handling of mixed NaN and non-NaN values."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "entry_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "optional_str": ["value", None],
                "optional_num": [100.0, None],
            }
        )

        result = dataframe_to_dict(df)

        assert result["optional_str"][0] == "value"
        assert result["optional_str"][1] == ""  # NaN converted
        assert result["optional_num"][0] == 100.0
        assert result["optional_num"][1] == 0  # NaN converted

    @pytest.mark.unit
    def test_dataframe_to_dict_resets_index(self):
        """Test index is reset in result."""
        # Use datetime index since implementation expects datetime index or datetime column
        dates = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "price": [100.0, 200.0],
            },
            index=dates,
        )
        df.index.name = "custom_index"

        result = dataframe_to_dict(df)

        # Index should not appear in result (reset_index drops it)
        assert "custom_index" not in result
        assert "ticker" in result
        assert len(result["ticker"]) == 2
        assert "datetime" in result
        assert len(result["datetime"]) == 2

    @pytest.mark.unit
    def test_dataframe_to_dict_complex_dataframe(self):
        """Test conversion of complex DataFrame with all features."""
        dates = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT", "GOOGL"],
                "entry_time": dates,
                "exit_time": dates + pd.Timedelta(days=1),
                "entry_price": [100.0, 200.0, 300.0],
                "exit_price": [105.0, 210.0, 315.0],
                "gross_pnl": [500.0, 1000.0, 1500.0],
                "side": ["LONG", "LONG", "SHORT"],
                "efficiency": [75.5, 80.0, None],
                "all_nan_col": [None, None, None],
            },
            index=dates,
        )

        result = dataframe_to_dict(df)

        assert "datetime" in result
        assert len(result["datetime"]) == 3
        assert "all_nan_col" not in result  # Dropped
        assert len(result["ticker"]) == 3
        assert result["efficiency"][2] == 0  # NaN converted to 0
        assert isinstance(result["entry_time"][0], int)  # Datetime converted
