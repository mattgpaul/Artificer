"""Unit and integration tests for TradeJournal.

Tests cover initialization, trade matching, metrics calculation, report generation,
account tracking, trade percentage position sizing, and complete workflows.
All external dependencies are mocked via conftest.py. Integration tests use
'debug' database.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.journal.journal import TradeJournal


class TestTradeJournalInitialization:
    """Test TradeJournal initialization."""

    @pytest.mark.unit
    def test_initialization_defaults(self):
        """Test initialization with default parameters."""
        signals = pd.DataFrame()
        journal = TradeJournal(signals=signals, strategy_name="TestStrategy")

        assert journal.signals.empty
        assert journal.strategy_name == "TestStrategy"
        assert journal.capital_per_trade == 10000.0
        assert journal.risk_free_rate == 0.04
        assert journal.initial_account_value is None
        assert journal.trade_percentage is None

    @pytest.mark.unit
    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        signals = pd.DataFrame()
        journal = TradeJournal(
            signals=signals,
            strategy_name="TestStrategy",
            ohlcv_data=pd.DataFrame(),
            capital_per_trade=20000.0,
            risk_free_rate=0.05,
        )

        assert journal.capital_per_trade == 20000.0
        assert journal.risk_free_rate == 0.05

    @pytest.mark.unit
    def test_initialization_account_tracking(self):
        """Test initialization with account tracking."""
        signals = pd.DataFrame()
        journal = TradeJournal(
            signals=signals,
            strategy_name="TestStrategy",
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )

        assert journal.initial_account_value == 50000.0
        assert journal.trade_percentage == 0.10


class TestTradeJournalMatchTrades:
    """Test match_trades method."""

    @pytest.mark.unit
    def test_match_trades_calls_match_trades_function(self):
        """Test match_trades calls the match_trades function."""
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

        journal = TradeJournal(signals=signals, strategy_name="TestStrategy")

        with patch(
            "system.algo_trader.strategy.journal.journal.match_trades"
        ) as mock_match:
            mock_match.return_value = pd.DataFrame()

            result = journal.match_trades()

            mock_match.assert_called_once()
            assert isinstance(result, pd.DataFrame)

    @pytest.mark.unit
    def test_match_trades_passes_parameters(self):
        """Test match_trades passes correct parameters."""
        signals = pd.DataFrame()
        ohlcv_data = pd.DataFrame()
        journal = TradeJournal(
            signals=signals,
            strategy_name="TestStrategy",
            ohlcv_data=ohlcv_data,
            capital_per_trade=15000.0,
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )

        with patch(
            "system.algo_trader.strategy.journal.journal.match_trades"
        ) as mock_match:
            mock_match.return_value = pd.DataFrame()

            journal.match_trades()

            call_args = mock_match.call_args
            assert call_args[0][0].equals(signals)
            assert call_args[0][1] == "TestStrategy"
            assert call_args[0][2] == 15000.0
            assert call_args[1]["ohlcv_data"].equals(ohlcv_data)
            assert call_args[1]["initial_account_value"] == 50000.0
            assert call_args[1]["trade_percentage"] == 0.10


class TestTradeJournalCalculateMetrics:
    """Test calculate_metrics method."""

    @pytest.mark.unit
    def test_calculate_metrics_calls_calculate_metrics_function(self):
        """Test calculate_metrics calls the calculate_metrics function."""
        signals = pd.DataFrame()
        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )

        journal = TradeJournal(signals=signals, strategy_name="TestStrategy")

        with patch(
            "system.algo_trader.strategy.journal.journal.calculate_metrics"
        ) as mock_calculate:
            mock_calculate.return_value = {"total_trades": 1}

            result = journal.calculate_metrics(trades)

            mock_calculate.assert_called_once()
            assert result == {"total_trades": 1}

    @pytest.mark.unit
    def test_calculate_metrics_passes_parameters(self):
        """Test calculate_metrics passes correct parameters."""
        signals = pd.DataFrame()
        trades = pd.DataFrame()
        journal = TradeJournal(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=15000.0,
            risk_free_rate=0.05,
        )

        with patch(
            "system.algo_trader.strategy.journal.journal.calculate_metrics"
        ) as mock_calculate:
            mock_calculate.return_value = {}

            journal.calculate_metrics(trades)

            call_args = mock_calculate.call_args
            assert call_args[0][0].equals(trades)
            assert call_args[0][1] == 15000.0
            assert call_args[0][2] == 0.05


class TestTradeJournalGenerateReport:
    """Test generate_report method."""

    @pytest.mark.unit
    def test_generate_report_complete_workflow(self):
        """Test generate_report complete workflow."""
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

        journal = TradeJournal(signals=signals, strategy_name="TestStrategy")

        mock_trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )

        mock_metrics = {"total_trades": 1, "total_profit": 500.0}

        with (
            patch(
                "system.algo_trader.strategy.journal.journal.match_trades"
            ) as mock_match,
            patch(
                "system.algo_trader.strategy.journal.journal.calculate_metrics"
            ) as mock_calculate,
        ):
            mock_match.return_value = mock_trades
            mock_calculate.return_value = mock_metrics

            metrics, trades = journal.generate_report()

            assert metrics == mock_metrics
            assert trades.equals(mock_trades)
            mock_match.assert_called_once()
            mock_calculate.assert_called_once_with(mock_trades, 10000.0, 0.04, journal.logger)

    @pytest.mark.unit
    def test_generate_report_empty_signals(self):
        """Test generate_report with empty signals."""
        signals = pd.DataFrame()
        journal = TradeJournal(signals=signals, strategy_name="TestStrategy")

        with (
            patch(
                "system.algo_trader.strategy.journal.journal.match_trades"
            ) as mock_match,
            patch(
                "system.algo_trader.strategy.journal.journal.calculate_metrics"
            ) as mock_calculate,
        ):
            mock_match.return_value = pd.DataFrame()
            mock_calculate.return_value = {}

            metrics, trades = journal.generate_report()

            assert metrics == {}
            assert trades.empty

    @pytest.mark.integration
    def test_generate_report_integration(self):
        """Test generate_report integration workflow."""
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

        journal = TradeJournal(
            signals=signals,
            strategy_name="TestStrategy",
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        mock_trades = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "entry_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "exit_time": [
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-11", tz="UTC"),
                ],
                "entry_price": [100.0, 200.0],
                "exit_price": [105.0, 210.0],
                "gross_pnl": [500.0, 1000.0],
            }
        )

        mock_metrics = {
            "total_trades": 2,
            "total_profit": 1500.0,
            "sharpe_ratio": 1.2,
        }

        with (
            patch(
                "system.algo_trader.strategy.journal.journal.match_trades"
            ) as mock_match,
            patch(
                "system.algo_trader.strategy.journal.journal.calculate_metrics"
            ) as mock_calculate,
        ):
            mock_match.return_value = mock_trades
            mock_calculate.return_value = mock_metrics

            metrics, trades = journal.generate_report()

            assert metrics["total_trades"] == 2
            assert len(trades) == 2
            assert trades.iloc[0]["ticker"] == "AAPL"
            assert trades.iloc[1]["ticker"] == "MSFT"

