"""Unit tests for SignalCollector - Signal Collection for Backtest Execution.

Tests cover signal collection, time windowing, signal deduplication, progress tracking,
and error handling. All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.signal_collector import SignalCollector


class TestSignalCollectorInitialization:
    """Test SignalCollector initialization."""

    def test_initialization_with_strategy(self, mock_logger):
        """Test initialization with strategy."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        assert collector.strategy == strategy
        assert collector.logger == mock_logger
        assert collector.lookback_bars is None

    def test_initialization_with_lookback_bars(self, mock_logger):
        """Test initialization with lookback_bars."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger, lookback_bars=50)

        assert collector.lookback_bars == 50

    def test_initialization_creates_logger_if_none(self):
        """Test initialization creates logger if not provided."""
        strategy = MagicMock()
        with patch("system.algo_trader.backtest.core.signal_collector.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            collector = SignalCollector(strategy)

            assert collector.logger == mock_logger


class TestSignalCollectorNormalization:
    """Test timestamp and index normalization methods."""

    def test_normalize_timestamp_without_tz(self, mock_logger):
        """Test normalizing timestamp without timezone."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        ts = pd.Timestamp("2024-01-01 10:00:00")
        result = collector._normalize_timestamp(ts)

        assert result.tz is not None
        # Check if timezone is UTC by comparing to UTC timezone
        assert str(result.tz) == "UTC" or result.tz.tzname(None) == "UTC"

    def test_normalize_timestamp_with_tz(self, mock_logger):
        """Test normalizing timestamp with timezone."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        ts = pd.Timestamp("2024-01-01 10:00:00", tz="America/New_York")
        result = collector._normalize_timestamp(ts)

        assert result.tz is not None
        # Check if timezone is UTC by comparing to UTC timezone
        assert str(result.tz) == "UTC" or result.tz.tzname(None) == "UTC"

    def test_normalize_index_without_tz(self, mock_logger):
        """Test normalizing index without timezone."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        data = pd.DataFrame(
            {"close": [100.0, 101.0]},
            index=pd.DatetimeIndex(["2024-01-01 10:00:00", "2024-01-01 11:00:00"]),
        )
        result = collector._normalize_index(data)

        assert result.index.tz is not None
        # Check if timezone is UTC by comparing to UTC timezone
        assert str(result.index.tz) == "UTC" or result.index.tz.tzname(None) == "UTC"

    def test_normalize_index_with_tz(self, mock_logger):
        """Test normalizing index with timezone."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        data = pd.DataFrame(
            {"close": [100.0, 101.0]},
            index=pd.DatetimeIndex(
                ["2024-01-01 10:00:00", "2024-01-01 11:00:00"], tz="America/New_York"
            ),
        )
        result = collector._normalize_index(data)

        assert result.index.tz is not None
        # Check if timezone is UTC by comparing to UTC timezone
        assert str(result.index.tz) == "UTC" or result.index.tz.tzname(None) == "UTC"

    def test_normalize_index_empty(self, mock_logger):
        """Test normalizing empty DataFrame."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        data = pd.DataFrame()
        result = collector._normalize_index(data)

        assert result.empty

    def test_normalize_index_none(self, mock_logger):
        """Test normalizing None."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        result = collector._normalize_index(None)

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestSignalCollectorWindowSlicing:
    """Test window slicing functionality."""

    def test_slice_window_with_lookback_bars(self, mock_logger):
        """Test slicing window with lookback_bars."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger, lookback_bars=5)

        data = pd.DataFrame(
            {"close": range(10)},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01", periods=10, freq="1H", tz="UTC")
            ),
        )
        current_time = pd.Timestamp("2024-01-01 10:00:00", tz="UTC")

        result = collector._slice_window(data, current_time)

        assert len(result) == 5
        assert result.index[-1] <= current_time

    def test_slice_window_with_strategy_window(self, mock_logger):
        """Test slicing window with strategy window."""
        strategy = MagicMock()
        strategy.window = 3
        collector = SignalCollector(strategy, logger=mock_logger)

        data = pd.DataFrame(
            {"close": range(10)},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01", periods=10, freq="1H", tz="UTC")
            ),
        )
        current_time = pd.Timestamp("2024-01-01 10:00:00", tz="UTC")

        result = collector._slice_window(data, current_time)

        assert len(result) == 3

    def test_slice_window_no_lookback(self, mock_logger):
        """Test slicing window without lookback."""
        strategy = MagicMock()
        strategy.window = None
        collector = SignalCollector(strategy, logger=mock_logger)

        data = pd.DataFrame(
            {"close": range(10)},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01", periods=10, freq="1H", tz="UTC")
            ),
        )
        current_time = pd.Timestamp("2024-01-01 10:00:00", tz="UTC")

        result = collector._slice_window(data, current_time)

        assert len(result) == 10

    def test_slice_window_empty_data(self, mock_logger):
        """Test slicing window with empty data."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        data = pd.DataFrame()
        current_time = pd.Timestamp("2024-01-01 10:00:00", tz="UTC")

        result = collector._slice_window(data, current_time)

        assert result.empty

    def test_slice_window_future_data(self, mock_logger):
        """Test slicing window with all future data."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        data = pd.DataFrame(
            {"close": range(10)},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-02", periods=10, freq="1H", tz="UTC")
            ),
        )
        current_time = pd.Timestamp("2024-01-01 10:00:00", tz="UTC")

        result = collector._slice_window(data, current_time)

        assert result.empty


class TestSignalCollectorSignalCollection:
    """Test signal collection for single and multiple tickers."""

    def test_collect_signals_for_ticker_single_signal(self, mock_logger):
        """Test collecting signals for a single ticker."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        ohlcv = pd.DataFrame(
            {"close": [100.0, 101.0, 102.0]},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01 10:00:00", periods=3, freq="1H", tz="UTC")
            ),
        )

        buy_signal = pd.DataFrame(
            {"price": [101.0]},
            index=pd.DatetimeIndex(["2024-01-01 11:00:00"], tz="UTC"),
        )
        sell_signal = pd.DataFrame()

        strategy.buy.return_value = buy_signal
        strategy.sell.return_value = sell_signal

        step_intervals = pd.DatetimeIndex(
            pd.date_range("2024-01-01 10:00:00", periods=3, freq="1H", tz="UTC")
        )
        data_cache = {"AAPL": ohlcv}

        with patch("system.algo_trader.backtest.core.signal_collector.ticker_progress_bar") as mock_pbar:
            mock_pbar.return_value.__enter__.return_value = None
            signals = collector.collect_signals_for_ticker("AAPL", step_intervals, data_cache)

            assert len(signals) == 1
            assert signals[0]["ticker"] == "AAPL"
            assert signals[0]["signal_type"] == "buy"
            assert signals[0]["price"] == 101.0

    def test_collect_signals_for_ticker_missing_ticker(self, mock_logger):
        """Test collecting signals for missing ticker."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        step_intervals = pd.DatetimeIndex(
            pd.date_range("2024-01-01 10:00:00", periods=3, freq="1H", tz="UTC")
        )
        data_cache = {}

        signals = collector.collect_signals_for_ticker("AAPL", step_intervals, data_cache)

        assert len(signals) == 0

    def test_collect_signals_for_ticker_empty_ohlcv(self, mock_logger):
        """Test collecting signals with empty OHLCV."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        step_intervals = pd.DatetimeIndex(
            pd.date_range("2024-01-01 10:00:00", periods=3, freq="1H", tz="UTC")
        )
        data_cache = {"AAPL": pd.DataFrame()}

        signals = collector.collect_signals_for_ticker("AAPL", step_intervals, data_cache)

        assert len(signals) == 0

    def test_collect_signals_for_all_tickers(self, mock_logger):
        """Test collecting signals for all tickers."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        ohlcv = pd.DataFrame(
            {"close": [100.0, 101.0]},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01 10:00:00", periods=2, freq="1H", tz="UTC")
            ),
        )

        buy_signal = pd.DataFrame(
            {"price": [101.0]},
            index=pd.DatetimeIndex(["2024-01-01 11:00:00"], tz="UTC"),
        )

        strategy.buy.return_value = buy_signal
        strategy.sell.return_value = pd.DataFrame()

        step_intervals = pd.DatetimeIndex(
            pd.date_range("2024-01-01 10:00:00", periods=2, freq="1H", tz="UTC")
        )
        data_cache = {"AAPL": ohlcv, "MSFT": ohlcv}

        signals = collector.collect_signals_for_all_tickers(step_intervals, ["AAPL", "MSFT"], data_cache)

        assert len(signals) >= 2
        assert all(s["ticker"] in ["AAPL", "MSFT"] for s in signals)

    def test_collect_signals_deduplication(self, mock_logger):
        """Test signal deduplication."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        ohlcv = pd.DataFrame(
            {"close": [100.0, 101.0]},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01 10:00:00", periods=2, freq="1H", tz="UTC")
            ),
        )

        buy_signal = pd.DataFrame(
            {"price": [101.0]},
            index=pd.DatetimeIndex(["2024-01-01 11:00:00"], tz="UTC"),
        )

        strategy.buy.return_value = buy_signal
        strategy.sell.return_value = pd.DataFrame()

        step_intervals = pd.DatetimeIndex(
            pd.date_range("2024-01-01 10:00:00", periods=2, freq="1H", tz="UTC")
        )
        data_cache = {"AAPL": ohlcv}

        with patch("system.algo_trader.backtest.core.signal_collector.ticker_progress_bar") as mock_pbar:
            mock_pbar.return_value.__enter__.return_value = None
            signals = collector.collect_signals_for_ticker("AAPL", step_intervals, data_cache)

            # Should not have duplicates
            signal_keys = {(s["ticker"], s["signal_time"], s["signal_type"], s["price"]) for s in signals}
            assert len(signal_keys) == len(signals)

    def test_collect_signals_error_handling(self, mock_logger):
        """Test error handling during signal collection."""
        strategy = MagicMock()
        collector = SignalCollector(strategy, logger=mock_logger)

        ohlcv = pd.DataFrame(
            {"close": [100.0, 101.0]},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01 10:00:00", periods=2, freq="1H", tz="UTC")
            ),
        )

        strategy.buy.side_effect = Exception("Test error")
        strategy.sell.return_value = pd.DataFrame()

        step_intervals = pd.DatetimeIndex(
            pd.date_range("2024-01-01 10:00:00", periods=2, freq="1H", tz="UTC")
        )
        data_cache = {"AAPL": ohlcv}

        with patch("system.algo_trader.backtest.core.signal_collector.ticker_progress_bar") as mock_pbar:
            mock_pbar.return_value.__enter__.return_value = None
            signals = collector.collect_signals_for_ticker("AAPL", step_intervals, data_cache)

            # Should continue despite errors
            assert isinstance(signals, list)
            mock_logger.error.assert_called()

