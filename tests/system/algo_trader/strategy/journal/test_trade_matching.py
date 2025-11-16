"""Unit and integration tests for trade_matching function.

Tests cover LONG/SHORT entry/exit matching, PnL calculation, efficiency calculation,
time held calculation, account tracking, trade percentage position sizing, and edge cases.
All external dependencies are mocked via conftest.py. Integration tests use 'debug' database.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from system.algo_trader.strategy.journal.trade_matching import match_trades


class TestMatchTradesEmptySignals:
    """Test match_trades with empty signals."""

    @pytest.mark.unit
    def test_match_trades_empty_dataframe(self):
        """Test matching empty signals DataFrame."""
        signals = pd.DataFrame()

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert result.empty

    @pytest.mark.unit
    def test_match_trades_no_signals(self):
        """Test matching with no signals."""
        signals = pd.DataFrame(columns=["ticker", "signal_time", "signal_type", "price", "side"])

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert result.empty


class TestMatchTradesLongPositions:
    """Test match_trades for LONG positions."""

    @pytest.mark.unit
    def test_match_trades_long_entry_exit(self):
        """Test matching LONG entry and exit signals."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                ],
                "signal_type": ["buy", "sell"],
                "price": [100.0, 105.0],
                "side": ["LONG", "LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert len(result) == 1
        assert result.iloc[0]["entry_price"] == 100.0
        assert result.iloc[0]["exit_price"] == 105.0
        assert result.iloc[0]["gross_pnl"] == 500.0  # 100 shares * $5
        assert result.iloc[0]["gross_pnl_pct"] == 5.0  # 5% return

    @pytest.mark.unit
    def test_match_trades_long_multiple_trades(self):
        """Test matching multiple LONG trades."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-15", tz="UTC"),
                    pd.Timestamp("2024-01-20", tz="UTC"),
                ],
                "signal_type": ["buy", "sell", "buy", "sell"],
                "price": [100.0, 105.0, 110.0, 115.0],
                "side": ["LONG", "LONG", "LONG", "LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert len(result) == 2
        assert result.iloc[0]["gross_pnl"] == 500.0
        # Second trade uses percentage-based sizing which results in different PnL
        assert abs(result.iloc[1]["gross_pnl"] - 454.5454545454545) < 0.01

    @pytest.mark.unit
    def test_match_trades_long_loss(self):
        """Test matching LONG trade with loss."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                ],
                "signal_type": ["buy", "sell"],
                "price": [100.0, 95.0],
                "side": ["LONG", "LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert len(result) == 1
        assert result.iloc[0]["gross_pnl"] == -500.0  # Loss
        assert result.iloc[0]["gross_pnl_pct"] == -5.0


class TestMatchTradesShortPositions:
    """Test match_trades for SHORT positions."""

    @pytest.mark.unit
    def test_match_trades_short_entry_exit(self):
        """Test matching SHORT entry and exit signals."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                ],
                "signal_type": ["sell", "buy"],
                "price": [100.0, 95.0],
                "side": ["SHORT", "SHORT"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert len(result) == 1
        assert result.iloc[0]["entry_price"] == 100.0
        assert result.iloc[0]["exit_price"] == 95.0
        assert result.iloc[0]["gross_pnl"] == 500.0  # Profit on short
        assert result.iloc[0]["gross_pnl_pct"] == 5.0

    @pytest.mark.unit
    def test_match_trades_short_loss(self):
        """Test matching SHORT trade with loss."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                ],
                "signal_type": ["sell", "buy"],
                "price": [100.0, 105.0],
                "side": ["SHORT", "SHORT"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert len(result) == 1
        assert result.iloc[0]["gross_pnl"] == -500.0  # Loss on short
        assert result.iloc[0]["gross_pnl_pct"] == -5.0


class TestMatchTradesMultipleTickers:
    """Test match_trades with multiple tickers."""

    @pytest.mark.unit
    def test_match_trades_multiple_tickers(self):
        """Test matching trades for multiple tickers."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                    pd.Timestamp("2024-01-11", tz="UTC"),
                ],
                "signal_type": ["buy", "sell", "buy", "sell"],
                "price": [100.0, 105.0, 200.0, 210.0],
                "side": ["LONG", "LONG", "LONG", "LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert len(result) == 2
        assert result.iloc[0]["ticker"] == "AAPL"
        assert result.iloc[1]["ticker"] == "MSFT"


class TestMatchTradesAccountTracking:
    """Test match_trades with account value tracking."""

    @pytest.mark.unit
    def test_match_trades_account_tracking(self):
        """Test account value tracking with trade percentage."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                ],
                "signal_type": ["buy", "sell"],
                "price": [100.0, 105.0],
                "side": ["LONG", "LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
            initial_account_value=50000.0,
            trade_percentage=0.10,  # 10% of account
        )

        assert len(result) == 1
        # Should use 10% of 50000 = 5000, buy 50 shares at $100
        assert result.iloc[0]["shares"] == 50
        assert result.iloc[0]["gross_pnl"] == 250.0  # 50 shares * $5

    @pytest.mark.unit
    def test_match_trades_account_tracking_multiple_trades(self):
        """Test account tracking across multiple trades."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-15", tz="UTC"),
                    pd.Timestamp("2024-01-20", tz="UTC"),
                ],
                "signal_type": ["buy", "sell", "buy", "sell"],
                "price": [100.0, 105.0, 110.0, 115.0],
                "side": ["LONG", "LONG", "LONG", "LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )

        assert len(result) == 2
        # First trade: 10% of 50000 = 5000, 50 shares
        assert result.iloc[0]["shares"] == 50
        # Second trade: 10% of (50000 + profit) = 10% of 50250 = 5025, ~45 shares
        # Account grows after first trade


class TestMatchTradesEfficiency:
    """Test efficiency calculation in match_trades."""

    @pytest.mark.unit
    def test_match_trades_efficiency_calculation(self):
        """Test efficiency calculation with OHLCV data."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                ],
                "signal_type": ["buy", "sell"],
                "price": [100.0, 105.0],
                "side": ["LONG", "LONG"],
            }
        )

        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0, 102.0, 104.0, 103.0, 105.0],
                "high": [105.0, 106.0, 107.0, 108.0, 110.0],
                "low": [99.0, 101.0, 103.0, 102.0, 104.0],
                "close": [102.0, 104.0, 106.0, 105.0, 107.0],
            },
            index=pd.date_range("2024-01-05", periods=5, freq="D", tz="UTC"),
        )

        with patch(
            "system.algo_trader.strategy.journal.trade_matching.calculate_efficiency"
        ) as mock_efficiency:
            mock_efficiency.return_value = 75.5

            result = match_trades(
                signals=signals,
                strategy_name="TestStrategy",
                capital_per_trade=10000.0,
                ohlcv_data=ohlcv_data,
            )

            assert len(result) == 1
            assert result.iloc[0]["efficiency"] == 75.5
            mock_efficiency.assert_called_once()


class TestMatchTradesTimeHeld:
    """Test time held calculation."""

    @pytest.mark.unit
    def test_match_trades_time_held_calculation(self):
        """Test time held calculation."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05 10:00:00", tz="UTC"),
                    pd.Timestamp("2024-01-10 14:00:00", tz="UTC"),
                ],
                "signal_type": ["buy", "sell"],
                "price": [100.0, 105.0],
                "side": ["LONG", "LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert len(result) == 1
        assert result.iloc[0]["time_held"] > 0
        # Should be approximately 5 days * 24 hours = 120 hours
        assert 115 < result.iloc[0]["time_held"] < 125


class TestMatchTradesUnmatchedPositions:
    """Test handling unmatched positions."""

    @pytest.mark.unit
    def test_match_trades_unmatched_entry(self):
        """Test unmatched entry signal (no exit)."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "signal_type": ["buy"],
                "price": [100.0],
                "side": ["LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        # Unmatched entry should not create a trade
        assert result.empty

    @pytest.mark.unit
    def test_match_trades_unmatched_exit(self):
        """Test unmatched exit signal (no entry)."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "signal_type": ["sell"],
                "price": [105.0],
                "side": ["LONG"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        # Unmatched exit should not create a trade
        assert result.empty


class TestMatchTradesEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.unit
    def test_match_trades_mixed_long_short(self):
        """Test matching mixed LONG and SHORT positions."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-15", tz="UTC"),
                    pd.Timestamp("2024-01-20", tz="UTC"),
                ],
                "signal_type": ["buy", "sell", "sell", "buy"],
                "price": [100.0, 105.0, 110.0, 95.0],
                "side": ["LONG", "LONG", "SHORT", "SHORT"],
            }
        )

        result = match_trades(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
        )

        assert len(result) == 2
        assert result.iloc[0]["side"] == "LONG"
        assert result.iloc[1]["side"] == "SHORT"

    @pytest.mark.integration
    def test_match_trades_complete_workflow(self):
        """Test complete trade matching workflow."""
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                    pd.Timestamp("2024-01-11", tz="UTC"),
                ],
                "signal_type": ["buy", "sell", "buy", "sell"],
                "price": [100.0, 105.0, 200.0, 210.0],
                "side": ["LONG", "LONG", "LONG", "LONG"],
            }
        )

        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0, 102.0, 104.0],
                "high": [105.0, 106.0, 107.0],
                "low": [99.0, 101.0, 103.0],
                "close": [102.0, 104.0, 106.0],
            },
            index=pd.date_range("2024-01-05", periods=3, freq="D", tz="UTC"),
        )

        with patch(
            "system.algo_trader.strategy.journal.trade_matching.calculate_efficiency"
        ) as mock_efficiency:
            mock_efficiency.return_value = 80.0

            result = match_trades(
                signals=signals,
                strategy_name="TestStrategy",
                capital_per_trade=10000.0,
                ohlcv_data=ohlcv_data,
            )

            assert len(result) == 2
            assert all(
                col in result.columns
                for col in [
                    "ticker",
                    "entry_time",
                    "exit_time",
                    "entry_price",
                    "exit_price",
                    "gross_pnl",
                    "gross_pnl_pct",
                    "efficiency",
                    "time_held",
                ]
            )
            assert result.iloc[0]["ticker"] == "AAPL"
            assert result.iloc[1]["ticker"] == "MSFT"
