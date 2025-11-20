"""Unit tests for backtest results Pydantic schemas.

Tests cover core validation behavior for BacktestTimeSeriesData,
BacktestTradesPayload, and BacktestMetricsPayload.
"""

import pytest

from system.algo_trader.backtest.results.schema import (
    BacktestMetricsPayload,
    BacktestStudiesPayload,
    BacktestTimeSeriesData,
    BacktestTradesPayload,
    ValidationError,
)


class TestBacktestTimeSeriesData:
    """Test BacktestTimeSeriesData validation."""

    @pytest.mark.unit
    def test_time_series_valid_payload(self):
        """Valid time-series payload passes validation."""
        payload = BacktestTimeSeriesData(
            datetime=[1704067200000, 1704153600000],
            price=[100.0, 101.0],
            side=["LONG", "LONG"],
        )
        assert len(payload.datetime) == 2
        assert payload.price == [100.0, 101.0]

    @pytest.mark.unit
    def test_time_series_empty_datetime_raises(self):
        """Empty datetime array is rejected."""
        with pytest.raises(ValidationError):
            BacktestTimeSeriesData(datetime=[], price=[])

    @pytest.mark.unit
    def test_time_series_mismatched_lengths_raises(self):
        """Mismatched column lengths are rejected."""
        with pytest.raises(ValidationError):
            BacktestTimeSeriesData(
                datetime=[1704067200000, 1704153600000],
                price=[100.0],  # length 1 vs 2
            )


class TestBacktestTradesPayload:
    """Test BacktestTradesPayload validation."""

    @pytest.mark.unit
    def test_trades_payload_valid(self):
        """Valid trades payload passes validation."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000],
            price=[100.0],
        )

        payload = BacktestTradesPayload(
            ticker="AAPL",
            strategy_name="TestStrategy",
            backtest_id="test-id",
            hash_id="abcdef1234567890",
            strategy_params={"short_window": 10, "long_window": 20},
            data=data,
            database="backtest-dev",
        )

        assert payload.ticker == "AAPL"
        assert payload.data.datetime == [1704067200000]

    @pytest.mark.unit
    def test_trades_payload_invalid_strategy_params_key_raises(self):
        """Empty strategy_params key is rejected."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000],
            price=[100.0],
        )

        with pytest.raises(ValidationError):
            BacktestTradesPayload(
                ticker="AAPL",
                strategy_name="TestStrategy",
                strategy_params={"": 10},
                data=data,
            )


class TestBacktestMetricsPayload:
    """Test BacktestMetricsPayload validation."""

    @pytest.mark.unit
    def test_metrics_payload_valid(self):
        """Valid metrics payload passes validation."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000],
            total_trades=[10],
        )

        payload = BacktestMetricsPayload(
            ticker="AAPL",
            strategy_name="TestStrategy",
            backtest_id="test-id",
            hash_id="abcdef1234567890",
            data=data,
            database="backtest-dev",
        )

        assert payload.ticker == "AAPL"
        assert payload.data.total_trades == [10]

    @pytest.mark.unit
    def test_metrics_payload_invalid_ticker_raises(self):
        """Empty ticker is rejected."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000],
            total_trades=[10],
        )

        with pytest.raises(ValidationError):
            BacktestMetricsPayload(
                ticker="",
                strategy_name="TestStrategy",
                data=data,
            )


class TestBacktestStudiesPayload:
    """Test BacktestStudiesPayload validation."""

    @pytest.mark.unit
    def test_studies_payload_valid(self):
        """Valid studies payload passes validation."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000, 1704153600000],
            sma_10=[100.0, 101.0],
            sma_20=[99.0, 100.0],
        )

        payload = BacktestStudiesPayload(
            ticker="AAPL",
            strategy_name="TestStrategy",
            backtest_id="test-id",
            hash_id="abcdef1234567890",
            strategy_params={"short_window": 10, "long_window": 20},
            data=data,
            database="backtest-dev",
        )

        assert payload.ticker == "AAPL"
        assert payload.strategy_name == "TestStrategy"
        assert payload.backtest_id == "test-id"
        assert payload.hash_id == "abcdef1234567890"
        assert payload.strategy_params == {"short_window": 10, "long_window": 20}
        assert payload.data.datetime == [1704067200000, 1704153600000]
        assert payload.data.sma_10 == [100.0, 101.0]

    @pytest.mark.unit
    def test_studies_payload_invalid_ticker_raises(self):
        """Empty ticker is rejected."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000],
            sma_10=[100.0],
        )

        with pytest.raises(ValidationError):
            BacktestStudiesPayload(
                ticker="",
                strategy_name="TestStrategy",
                data=data,
            )

    @pytest.mark.unit
    def test_studies_payload_invalid_strategy_name_raises(self):
        """Empty strategy_name is rejected."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000],
            sma_10=[100.0],
        )

        with pytest.raises(ValidationError):
            BacktestStudiesPayload(
                ticker="AAPL",
                strategy_name="",
                data=data,
            )

    @pytest.mark.unit
    def test_studies_payload_invalid_strategy_params_key_raises(self):
        """Empty strategy_params key is rejected."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000],
            sma_10=[100.0],
        )

        with pytest.raises(ValidationError):
            BacktestStudiesPayload(
                ticker="AAPL",
                strategy_name="TestStrategy",
                strategy_params={"": 10},
                data=data,
            )

    @pytest.mark.unit
    def test_studies_payload_none_strategy_params(self):
        """None strategy_params is allowed."""
        data = BacktestTimeSeriesData(
            datetime=[1704067200000],
            sma_10=[100.0],
        )

        payload = BacktestStudiesPayload(
            ticker="AAPL",
            strategy_name="TestStrategy",
            strategy_params=None,
            data=data,
        )

        assert payload.strategy_params is None

    @pytest.mark.unit
    def test_studies_payload_mismatched_data_lengths_raises(self):
        """Mismatched data column lengths are rejected."""
        with pytest.raises(ValidationError):
            BacktestStudiesPayload(
                ticker="AAPL",
                strategy_name="TestStrategy",
                data=BacktestTimeSeriesData(
                    datetime=[1704067200000, 1704153600000],
                    sma_10=[100.0],  # length 1 vs 2
                ),
            )
