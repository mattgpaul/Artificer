"""Unit tests for PositionManager and PositionManagerConfig.

Tests cover configuration, signal filtering (entry/exit), position state tracking,
and edge cases. All external dependencies are mocked via conftest.py.
"""

import pandas as pd
import pytest

from system.algo_trader.strategy.position_manager.position_manager import (
    PositionManager,
    PositionManagerConfig,
)


class TestPositionManagerConfig:
    """Test PositionManagerConfig dataclass."""

    @pytest.mark.unit
    def test_default_initialization(self):
        """Test default initialization."""
        config = PositionManagerConfig()
        assert config.allow_scale_in is False

    @pytest.mark.unit
    def test_custom_initialization(self):
        """Test initialization with custom values."""
        config = PositionManagerConfig(allow_scale_in=True)
        assert config.allow_scale_in is True

    @pytest.mark.unit
    def test_from_dict_defaults(self):
        """Test from_dict with missing keys uses defaults."""
        config = PositionManagerConfig.from_dict({})
        assert config.allow_scale_in is False

    @pytest.mark.unit
    def test_from_dict_with_values(self):
        """Test from_dict with provided values."""
        config = PositionManagerConfig.from_dict({"allow_scale_in": True})
        assert config.allow_scale_in is True

    @pytest.mark.unit
    def test_to_dict(self):
        """Test to_dict serialization."""
        config = PositionManagerConfig(allow_scale_in=True)
        result = config.to_dict()
        assert result == {"allow_scale_in": True}


class TestPositionManagerInitialization:
    """Test PositionManager initialization."""

    @pytest.mark.unit
    def test_initialization_with_config(self, default_config, mock_logger):
        """Test initialization with config."""
        manager = PositionManager(default_config)
        assert manager.config == default_config
        assert manager.logger is not None

    @pytest.mark.unit
    def test_initialization_with_custom_logger(self, default_config):
        """Test initialization with custom logger."""
        custom_logger = "custom_logger"
        manager = PositionManager(default_config, logger=custom_logger)
        assert manager.logger == custom_logger


class TestPositionManagerApplyEmptySignals:
    """Test apply method with empty signals."""

    @pytest.mark.unit
    def test_apply_empty_dataframe(self, default_config):
        """Test apply with empty DataFrame returns empty DataFrame."""
        manager = PositionManager(default_config)
        signals = pd.DataFrame()
        result = manager.apply(signals)
        assert result.empty

    @pytest.mark.unit
    def test_apply_empty_dataframe_with_scale_in(self, scale_in_config):
        """Test apply with empty DataFrame and scale_in enabled."""
        manager = PositionManager(scale_in_config)
        signals = pd.DataFrame()
        result = manager.apply(signals)
        assert result.empty


class TestPositionManagerApplyScaleIn:
    """Test apply method with scale_in enabled."""

    @pytest.mark.unit
    def test_apply_scale_in_returns_all_signals(
        self, scale_in_config, sample_signals_long_entry_exit
    ):
        """Test apply with scale_in enabled returns all signals unchanged."""
        manager = PositionManager(scale_in_config)
        result = manager.apply(sample_signals_long_entry_exit)
        assert len(result) == len(sample_signals_long_entry_exit)
        pd.testing.assert_frame_equal(result, sample_signals_long_entry_exit)


class TestPositionManagerApplyMissingColumns:
    """Test apply method with missing required columns."""

    @pytest.mark.unit
    def test_apply_missing_ticker_column(self, default_config):
        """Test apply with missing ticker column returns unchanged signals."""
        manager = PositionManager(default_config)
        signals = pd.DataFrame({"signal_type": ["buy"], "price": [100.0]})
        result = manager.apply(signals)
        # Should return signals unchanged when required columns are missing
        pd.testing.assert_frame_equal(result, signals)

    @pytest.mark.unit
    def test_apply_missing_signal_type_column(self, default_config):
        """Test apply with missing signal_type column returns unchanged signals."""
        manager = PositionManager(default_config)
        signals = pd.DataFrame({"ticker": ["AAPL"], "price": [100.0]})
        result = manager.apply(signals)
        # Should return signals unchanged when required columns are missing
        pd.testing.assert_frame_equal(result, signals)


class TestPositionManagerApplyLongPositions:
    """Test apply method with LONG positions."""

    @pytest.mark.unit
    def test_apply_long_entry_exit_cycle(self, default_config, sample_signals_long_entry_exit):
        """Test apply filters LONG entry/exit cycle correctly."""
        manager = PositionManager(default_config)
        result = manager.apply(sample_signals_long_entry_exit)

        # Should allow first buy (entry), filter second buy (already in position),
        # allow sell (exit), allow second ticker's buy and sell
        assert len(result) == 4
        assert result.iloc[0]["signal_type"] == "buy"
        assert result.iloc[1]["signal_type"] == "sell"
        assert result.iloc[2]["signal_type"] == "buy"
        assert result.iloc[3]["signal_type"] == "sell"

    @pytest.mark.unit
    def test_apply_long_multiple_entries_filtered(
        self, default_config, sample_signals_multiple_entries
    ):
        """Test apply filters multiple entry attempts for LONG position."""
        manager = PositionManager(default_config)
        result = manager.apply(sample_signals_multiple_entries)

        # Should allow first buy, filter subsequent buys until sell, then allow final buy
        assert len(result) == 3
        assert result.iloc[0]["signal_type"] == "buy"
        assert result.iloc[1]["signal_type"] == "sell"
        assert result.iloc[2]["signal_type"] == "buy"

    @pytest.mark.unit
    def test_apply_long_exit_without_entry_filtered(
        self, default_config, sample_signals_exit_without_entry
    ):
        """Test apply filters exit signal when no position is open."""
        manager = PositionManager(default_config)
        result = manager.apply(sample_signals_exit_without_entry)

        # Should filter first sell (no position), allow buy, allow sell
        assert len(result) == 2
        assert result.iloc[0]["signal_type"] == "buy"
        assert result.iloc[1]["signal_type"] == "sell"


class TestPositionManagerApplyShortPositions:
    """Test apply method with SHORT positions."""

    @pytest.mark.unit
    def test_apply_short_entry_exit_cycle(self, default_config, sample_signals_short_entry_exit):
        """Test apply filters SHORT entry/exit cycle correctly."""
        manager = PositionManager(default_config)
        result = manager.apply(sample_signals_short_entry_exit)

        # For SHORT: sell is entry, buy is exit
        # Should allow first sell (entry), allow buy (exit), allow second ticker's sell and buy
        assert len(result) == 4
        assert result.iloc[0]["signal_type"] == "sell"
        assert result.iloc[1]["signal_type"] == "buy"
        assert result.iloc[2]["signal_type"] == "sell"
        assert result.iloc[3]["signal_type"] == "buy"


class TestPositionManagerApplyEdgeCases:
    """Test apply method edge cases."""

    @pytest.mark.unit
    def test_apply_no_signal_time_column(self, default_config, sample_signals_no_time_column):
        """Test apply works without signal_time column."""
        manager = PositionManager(default_config)
        result = manager.apply(sample_signals_no_time_column)

        # Should still filter correctly using index
        assert len(result) == 2
        assert result.iloc[0]["signal_type"] == "buy"
        assert result.iloc[1]["signal_type"] == "sell"

    @pytest.mark.unit
    def test_apply_all_signals_filtered_returns_empty(self, default_config):
        """Test apply returns empty DataFrame when all signals are filtered."""
        manager = PositionManager(default_config)
        # Exit signal without entry - should be filtered
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_type": ["sell"],
                "side": ["LONG"],
            },
            index=[0],
        )
        result = manager.apply(signals)
        assert result.empty

    @pytest.mark.unit
    def test_apply_with_ohlcv_by_ticker(
        self, default_config, sample_signals_long_entry_exit, sample_ohlcv_by_ticker
    ):
        """Test apply accepts ohlcv_by_ticker parameter (currently unused but should not error)."""
        manager = PositionManager(default_config)
        result = manager.apply(sample_signals_long_entry_exit, sample_ohlcv_by_ticker)
        assert len(result) == 4

    @pytest.mark.unit
    def test_apply_default_side_is_long(self, default_config):
        """Test apply defaults side to LONG when not provided."""
        manager = PositionManager(default_config)
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_type": ["buy", "sell"],
            },
            index=[0, 1],
        )
        result = manager.apply(signals)
        # Should work as LONG position
        assert len(result) == 2
        assert result.iloc[0]["signal_type"] == "buy"
        assert result.iloc[1]["signal_type"] == "sell"

    @pytest.mark.unit
    def test_apply_multiple_tickers_independent(self, default_config):
        """Test apply handles multiple tickers independently."""
        manager = PositionManager(default_config)
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
                "signal_type": ["buy", "buy", "sell", "sell"],
                "side": ["LONG", "LONG", "LONG", "LONG"],
            },
            index=[0, 1, 2, 3],
        )
        result = manager.apply(signals)
        # Both tickers should have their entry/exit cycles
        assert len(result) == 4
        assert set(result["ticker"].unique()) == {"AAPL", "MSFT"}
