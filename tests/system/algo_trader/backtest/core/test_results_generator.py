"""Unit and integration tests for ResultsGenerator.

Tests cover initialization, results generation from signals (single/multiple tickers),
execution simulation integration, and account tracking. All external dependencies
are mocked via conftest.py. Integration tests use 'debug' database.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig, ExecutionSimulator
from system.algo_trader.backtest.core.results_generator import BacktestResults, ResultsGenerator


class TestResultsGeneratorInitialization:
    """Test ResultsGenerator initialization."""

    @pytest.mark.unit
    def test_initialization_defaults(self, mock_strategy):
        """Test initialization with default parameters."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())

        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        assert generator.strategy == mock_strategy
        assert generator.execution_simulator == execution_simulator
        assert generator.capital_per_trade == 10000.0
        assert generator.risk_free_rate == 0.04
        assert generator.initial_account_value is None
        assert generator.trade_percentage is None

    @pytest.mark.unit
    def test_initialization_custom_params(self, mock_strategy):
        """Test initialization with custom parameters."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        custom_logger = MagicMock()

        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=20000.0,
            risk_free_rate=0.05,
            logger=custom_logger,
        )

        assert generator.capital_per_trade == 20000.0
        assert generator.risk_free_rate == 0.05
        assert generator.logger == custom_logger

    @pytest.mark.unit
    def test_initialization_account_tracking(self, mock_strategy):
        """Test initialization with account tracking."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())

        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )

        assert generator.initial_account_value == 50000.0
        assert generator.trade_percentage == 0.10


class TestResultsGeneratorFromSignals:
    """Test generate_results_from_signals method."""

    @pytest.mark.unit
    def test_generate_results_from_signals_empty_signals(self, mock_strategy):
        """Test generating results from empty signals."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        signals = pd.DataFrame()
        ticker_data = pd.DataFrame()

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            results = generator.generate_results_from_signals(signals, "AAPL", ticker_data)

            assert isinstance(results, BacktestResults)
            assert results.signals.empty
            assert results.trades.empty
            assert results.metrics == {}

    @pytest.mark.unit
    def test_generate_results_from_signals_with_trades(self, mock_strategy):
        """Test generating results from signals with trades."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "signal_type": ["buy"],
                "price": [100.0],
            }
        )
        ticker_data = pd.DataFrame(
            {
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [104.0],
                "volume": [1000000],
            },
            index=[pd.Timestamp("2024-01-05", tz="UTC")],
        )

        mock_trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [104.0],
                "gross_pnl": [400.0],
            }
        )

        with (
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
        ):
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = (
                {"total_trades": 1, "total_profit": 400.0},
                mock_trades,
            )
            mock_journal_class.return_value = mock_journal

            execution_simulator.apply_execution = MagicMock(return_value=mock_trades)

            results = generator.generate_results_from_signals(signals, "AAPL", ticker_data)

            assert isinstance(results, BacktestResults)
            assert not results.signals.empty
            assert not results.trades.empty
            assert results.metrics["total_trades"] == 1
            assert results.strategy_name == mock_strategy.strategy_name

    @pytest.mark.unit
    def test_generate_results_from_signals_no_trades(self, mock_strategy):
        """Test generating results when no trades matched."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "signal_type": ["buy"],
                "price": [100.0],
            }
        )
        ticker_data = pd.DataFrame()

        with (
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
            patch.object(execution_simulator, "apply_execution") as mock_apply_execution,
        ):
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            results = generator.generate_results_from_signals(signals, "AAPL", ticker_data)

            assert isinstance(results, BacktestResults)
            assert not results.signals.empty
            assert results.trades.empty
            mock_apply_execution.assert_not_called()

    @pytest.mark.integration
    def test_generate_results_from_signals_complete_workflow(self, mock_strategy):
        """Test complete workflow: signals → TradeJournal → ExecutionSimulator."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

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
        ticker_data = pd.DataFrame(
            {
                "open": [100.0, 105.0],
                "high": [105.0, 110.0],
                "low": [99.0, 104.0],
                "close": [104.0, 108.0],
                "volume": [1000000, 1000000],
            },
            index=[
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
        )

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

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = (
                {"total_trades": 1, "total_profit": 500.0},
                mock_trades,
            )
            mock_journal_class.return_value = mock_journal

            executed_trades = pd.DataFrame(
                {
                    "ticker": ["AAPL"],
                    "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                    "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                    "entry_price": [100.0],
                    "exit_price": [105.0],
                    "gross_pnl": [500.0],
                    "net_pnl": [495.0],
                }
            )
            execution_simulator.apply_execution = MagicMock(return_value=executed_trades)

            results = generator.generate_results_from_signals(signals, "AAPL", ticker_data)

            assert isinstance(results, BacktestResults)
            assert not results.trades.empty
            assert len(results.trades) == 1
            assert results.trades.iloc[0]["net_pnl"] == 495.0
            execution_simulator.apply_execution.assert_called_once()

    @pytest.mark.integration
    def test_generate_results_from_signals_account_tracking(self, mock_strategy):
        """Test generating results with account tracking."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )

        signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "signal_type": ["buy"],
                "price": [100.0],
            }
        )
        ticker_data = pd.DataFrame()

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            generator.generate_results_from_signals(signals, "AAPL", ticker_data)

            # Verify account tracking parameters passed to TradeJournal
            call_args = mock_journal_class.call_args
            assert call_args[1]["initial_account_value"] == 50000.0
            assert call_args[1]["trade_percentage"] == 0.10


class TestResultsGeneratorForAllTickers:
    """Test generate_results_for_all_tickers method."""

    @pytest.mark.unit
    def test_generate_results_for_all_tickers_empty_signals(self, mock_strategy):
        """Test generating results from empty signals."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        # Create empty DataFrame with required columns to match implementation expectations
        combined_signals = pd.DataFrame(
            columns=["ticker", "signal_time", "signal_type", "price", "side"]
        )
        data_cache = {}

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as _mock_journal_class:
            results = generator.generate_results_for_all_tickers(combined_signals, data_cache)

            assert isinstance(results, BacktestResults)
            assert results.signals.empty
            assert results.trades.empty
            assert results.metrics == {}

    @pytest.mark.unit
    def test_generate_results_for_all_tickers_single_ticker(self, mock_strategy):
        """Test generating results for single ticker."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        combined_signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "signal_type": ["buy"],
                "price": [100.0],
            }
        )
        ticker_data = pd.DataFrame()
        data_cache = {"AAPL": ticker_data}

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

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, mock_trades)
            mock_journal.calculate_metrics.return_value = {"total_trades": 1}
            mock_journal_class.return_value = mock_journal

            execution_simulator.apply_execution = MagicMock(return_value=mock_trades)

            results = generator.generate_results_for_all_tickers(combined_signals, data_cache)

            assert isinstance(results, BacktestResults)
            assert not results.signals.empty
            assert not results.trades.empty
            assert results.metrics["total_trades"] == 1

    @pytest.mark.unit
    def test_generate_results_for_all_tickers_multiple_tickers(self, mock_strategy):
        """Test generating results for multiple tickers."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        combined_signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "signal_type": ["buy", "buy"],
                "price": [100.0, 200.0],
            }
        )
        data_cache = {
            "AAPL": pd.DataFrame(),
            "MSFT": pd.DataFrame(),
        }

        mock_trades_aapl = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )
        mock_trades_msft = pd.DataFrame(
            {
                "ticker": ["MSFT"],
                "entry_time": [pd.Timestamp("2024-01-06", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-11", tz="UTC")],
                "entry_price": [200.0],
                "exit_price": [210.0],
                "gross_pnl": [1000.0],
            }
        )

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            # First call for AAPL, second for MSFT, third for group metrics
            mock_journal.generate_report.side_effect = [
                ({}, mock_trades_aapl),
                ({}, mock_trades_msft),
            ]
            mock_journal.calculate_metrics.return_value = {
                "total_trades": 2,
                "total_profit": 1500.0,
            }
            mock_journal_class.return_value = mock_journal

            combined_trades = pd.concat([mock_trades_aapl, mock_trades_msft], ignore_index=True)
            execution_simulator.apply_execution = MagicMock(return_value=combined_trades)

            results = generator.generate_results_for_all_tickers(combined_signals, data_cache)

            assert isinstance(results, BacktestResults)
            assert len(results.signals) == 2
            assert len(results.trades) == 2
            assert results.metrics["total_trades"] == 2
            assert results.metrics["total_profit"] == 1500.0
            # Should create journal for each ticker plus one for group metrics
            assert mock_journal_class.call_count == 3

    @pytest.mark.unit
    def test_generate_results_for_all_tickers_missing_data(self, mock_strategy):
        """Test generating results when ticker data missing from cache."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        combined_signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "MISSING"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "signal_type": ["buy", "buy"],
                "price": [100.0, 200.0],
            }
        )
        data_cache = {"AAPL": pd.DataFrame()}  # MISSING not in cache

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            results = generator.generate_results_for_all_tickers(combined_signals, data_cache)

            # Should handle missing ticker gracefully
            assert isinstance(results, BacktestResults)
            # Should create journal for each ticker (even if data missing)
            assert mock_journal_class.call_count == 2

    @pytest.mark.integration
    def test_generate_results_for_all_tickers_complete_workflow(self, mock_strategy):
        """Test complete workflow for multiple tickers."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
        )

        combined_signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "signal_type": ["buy", "buy"],
                "price": [100.0, 200.0],
            }
        )
        data_cache = {
            "AAPL": pd.DataFrame(),
            "MSFT": pd.DataFrame(),
        }

        mock_trades_aapl = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
            }
        )
        mock_trades_msft = pd.DataFrame(
            {
                "ticker": ["MSFT"],
                "entry_time": [pd.Timestamp("2024-01-06", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-11", tz="UTC")],
                "entry_price": [200.0],
                "exit_price": [210.0],
                "gross_pnl": [1000.0],
            }
        )

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.side_effect = [
                ({}, mock_trades_aapl),
                ({}, mock_trades_msft),
            ]
            mock_journal.calculate_metrics.return_value = {
                "total_trades": 2,
                "total_profit": 1500.0,
                "sharpe_ratio": 1.2,
            }
            mock_journal_class.return_value = mock_journal

            combined_trades = pd.concat([mock_trades_aapl, mock_trades_msft], ignore_index=True)
            executed_trades = combined_trades.copy()
            executed_trades["net_pnl"] = [495.0, 990.0]
            execution_simulator.apply_execution = MagicMock(return_value=executed_trades)

            results = generator.generate_results_for_all_tickers(combined_signals, data_cache)

            assert isinstance(results, BacktestResults)
            assert len(results.trades) == 2
            assert results.metrics["total_trades"] == 2
            assert results.metrics["total_profit"] == 1500.0
            execution_simulator.apply_execution.assert_called_once()

    @pytest.mark.integration
    def test_generate_results_for_all_tickers_account_tracking(self, mock_strategy):
        """Test generating results with account tracking across multiple tickers."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )

        combined_signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "signal_type": ["buy", "buy"],
                "price": [100.0, 200.0],
            }
        )
        data_cache = {
            "AAPL": pd.DataFrame(),
            "MSFT": pd.DataFrame(),
        }

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal.calculate_metrics.return_value = {}
            mock_journal_class.return_value = mock_journal

            generator.generate_results_for_all_tickers(combined_signals, data_cache)

            # Verify account tracking parameters passed to all TradeJournal instances
            call_args_list = mock_journal_class.call_args_list
            for call_args in call_args_list:
                assert call_args[1]["initial_account_value"] == 50000.0
                assert call_args[1]["trade_percentage"] == 0.10


class TestResultsGeneratorPositionManager:
    """Test ResultsGenerator with PositionManager integration."""

    @pytest.mark.integration
    def test_generate_results_from_signals_with_position_manager_filters_entries(
        self, mock_strategy, position_manager
    ):
        """Test position_manager filters multiple entry signals correctly."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            position_manager=position_manager,
        )

        # Signals with multiple buy attempts (should filter duplicates)
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                    pd.Timestamp("2024-01-07", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                ],
                "signal_type": ["buy", "buy", "buy", "sell"],
                "price": [100.0, 101.0, 102.0, 105.0],
                "side": ["LONG", "LONG", "LONG", "LONG"],
            }
        )
        ticker_data = pd.DataFrame()

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            # Only first buy and sell should result in trades
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
            mock_journal.generate_report.return_value = (
                {"total_trades": 1, "total_profit": 500.0},
                mock_trades,
            )
            mock_journal_class.return_value = mock_journal

            execution_simulator.apply_execution = MagicMock(return_value=mock_trades)

            results = generator.generate_results_from_signals(signals, "AAPL", ticker_data)

            # Position manager should filter to only first buy and sell
            assert isinstance(results, BacktestResults)
            assert len(results.signals) == 2  # First buy and sell only
            assert results.signals.iloc[0]["signal_type"] == "buy"
            assert results.signals.iloc[1]["signal_type"] == "sell"
            assert not results.trades.empty

    @pytest.mark.integration
    def test_generate_results_from_signals_with_position_manager_filters_all_signals(
        self, mock_strategy, position_manager
    ):
        """Test position_manager filters all signals when exit comes before entry."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            position_manager=position_manager,
        )

        # Exit signal before entry (should filter exit, then allow entry)
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "signal_type": ["sell", "buy"],
                "price": [100.0, 101.0],
                "side": ["LONG", "LONG"],
            }
        )
        ticker_data = pd.DataFrame()

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            results = generator.generate_results_from_signals(signals, "AAPL", ticker_data)

            # Position manager should filter exit (no position), allow buy
            assert isinstance(results, BacktestResults)
            assert len(results.signals) == 1
            assert results.signals.iloc[0]["signal_type"] == "buy"
            assert results.trades.empty

    @pytest.mark.integration
    def test_generate_results_for_all_tickers_with_position_manager(
        self, mock_strategy, position_manager
    ):
        """Test position_manager integration with multiple tickers."""
        execution_simulator = ExecutionSimulator(ExecutionConfig())
        generator = ResultsGenerator(
            strategy=mock_strategy,
            execution_simulator=execution_simulator,
            capital_per_trade=10000.0,
            risk_free_rate=0.04,
            position_manager=position_manager,
        )

        # Multiple tickers with multiple entry attempts
        combined_signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "MSFT", "MSFT", "MSFT"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-10", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                    pd.Timestamp("2024-01-07", tz="UTC"),
                    pd.Timestamp("2024-01-11", tz="UTC"),
                ],
                "signal_type": ["buy", "sell", "buy", "buy", "sell"],
                "price": [100.0, 105.0, 200.0, 201.0, 210.0],
                "side": ["LONG", "LONG", "LONG", "LONG", "LONG"],
            }
        )
        data_cache = {
            "AAPL": pd.DataFrame(),
            "MSFT": pd.DataFrame(),
        }

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_trades_aapl = pd.DataFrame(
                {
                    "ticker": ["AAPL"],
                    "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                    "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
                    "entry_price": [100.0],
                    "exit_price": [105.0],
                    "gross_pnl": [500.0],
                }
            )
            mock_trades_msft = pd.DataFrame(
                {
                    "ticker": ["MSFT"],
                    "entry_time": [pd.Timestamp("2024-01-06", tz="UTC")],
                    "exit_time": [pd.Timestamp("2024-01-11", tz="UTC")],
                    "entry_price": [200.0],
                    "exit_price": [210.0],
                    "gross_pnl": [1000.0],
                }
            )
            mock_journal.generate_report.side_effect = [
                ({}, mock_trades_aapl),
                ({}, mock_trades_msft),
            ]
            mock_journal.calculate_metrics.return_value = {
                "total_trades": 2,
                "total_profit": 1500.0,
            }
            mock_journal_class.return_value = mock_journal

            combined_trades = pd.concat([mock_trades_aapl, mock_trades_msft], ignore_index=True)
            execution_simulator.apply_execution = MagicMock(return_value=combined_trades)

            results = generator.generate_results_for_all_tickers(combined_signals, data_cache)

            # Position manager should filter MSFT's second buy (duplicate entry)
            assert isinstance(results, BacktestResults)
            assert len(results.signals) == 4  # AAPL: buy+sell, MSFT: buy+sell (second buy filtered)
            assert results.metrics["total_trades"] == 2
