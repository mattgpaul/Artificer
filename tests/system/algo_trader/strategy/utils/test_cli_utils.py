"""Unit tests for cli_utils.py - CLI utility functions.

Tests cover ticker resolution (including full-registry), signal formatting,
journal summary formatting, and trade details formatting. External dependencies
(Tickers, logger) are mocked.
"""

from datetime import datetime

import pandas as pd
import pytest

from system.algo_trader.strategy.utils.cli_utils import (
    format_journal_summary,
    format_signal_summary,
    format_trade_details,
    get_influxdb_tickers,
    resolve_tickers,
)

# All fixtures moved to conftest.py


class TestResolveTickers:
    """Test ticker resolution functionality."""

    def test_resolve_specific_tickers(self, mock_logger):
        """Test resolving specific ticker list."""
        tickers = ["AAPL", "MSFT", "GOOGL"]

        result = resolve_tickers(tickers, mock_logger)

        assert result == tickers
        mock_logger.info.assert_called_once()
        assert "Processing 3 specific tickers" in mock_logger.info.call_args[0][0]

    def test_resolve_single_ticker(self, mock_logger):
        """Test resolving single ticker."""
        tickers = ["AAPL"]

        result = resolve_tickers(tickers, mock_logger)

        assert result == ["AAPL"]
        mock_logger.info.assert_called_once()

    def test_resolve_full_registry(self, mock_tickers_class, mock_logger):
        """Test resolving full-registry to fetch all SEC tickers."""
        # Mock SEC API response
        mock_tickers_class["instance"].get_tickers.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
            "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
        }

        result = resolve_tickers(["full-registry"], mock_logger)

        assert len(result) == 3
        assert "AAPL" in result
        assert "MSFT" in result
        assert "GOOGL" in result

        # Verify logging
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("full-registry specified" in msg for msg in info_calls)
        assert any("Retrieved 3 tickers" in msg for msg in info_calls)

    def test_resolve_full_registry_api_failure(self, mock_tickers_class, mock_logger):
        """Test full-registry when SEC API returns None."""
        mock_tickers_class["instance"].get_tickers.return_value = None

        with pytest.raises(ValueError, match="Failed to retrieve tickers from SEC datasource"):
            resolve_tickers(["full-registry"], mock_logger)

        mock_logger.error.assert_called_once()

    def test_resolve_full_registry_empty_response(self, mock_tickers_class, mock_logger):
        """Test full-registry with empty SEC response."""
        mock_tickers_class["instance"].get_tickers.return_value = {}

        result = resolve_tickers(["full-registry"], mock_logger)

        assert result == []

    def test_resolve_full_registry_malformed_data(self, mock_tickers_class, mock_logger):
        """Test full-registry with malformed SEC data."""
        # Malformed data - missing ticker field
        mock_tickers_class["instance"].get_tickers.return_value = {
            "0": {"cik_str": 320193, "title": "Apple Inc."},  # Missing ticker
            "1": {"cik_str": 789019, "ticker": "MSFT"},  # Valid
            "2": "invalid_value",  # Not a dict
        }

        result = resolve_tickers(["full-registry"], mock_logger)

        # Should only extract MSFT
        assert result == ["MSFT"]

    def test_resolve_full_registry_large_dataset(self, mock_tickers_class, mock_logger):
        """Test full-registry with large number of tickers."""
        # Generate 1000 mock tickers
        mock_data = {
            str(i): {"cik_str": i, "ticker": f"TICK{i}", "title": f"Company {i}"}
            for i in range(1000)
        }
        mock_tickers_class["instance"].get_tickers.return_value = mock_data

        result = resolve_tickers(["full-registry"], mock_logger)

        assert len(result) == 1000
        assert "TICK0" in result
        assert "TICK999" in result

    def test_resolve_sp500(self, mock_get_sp500, mock_logger):
        """Test resolving SP500 to fetch S&P 500 tickers."""
        mock_sp500_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        mock_get_sp500.return_value = mock_sp500_tickers

        result = resolve_tickers(["SP500"], mock_logger)

        assert result == mock_sp500_tickers
        assert len(result) == 5
        assert "AAPL" in result
        assert "NVDA" in result

        # Verify logging
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("SP500 specified" in msg for msg in info_calls)
        assert any("Retrieved 5 S&P 500 tickers" in msg for msg in info_calls)

    def test_resolve_sp500_empty_list(self, mock_get_sp500, mock_logger):
        """Test SP500 when get_sp500_tickers returns empty list."""
        mock_get_sp500.return_value = []

        with pytest.raises(ValueError, match="Failed to retrieve S&P 500 tickers"):
            resolve_tickers(["SP500"], mock_logger)

        mock_logger.error.assert_called_once()

    def test_resolve_sp500_large_dataset(self, mock_get_sp500, mock_logger):
        """Test SP500 with large number of tickers."""
        # Generate mock S&P 500 tickers (typically ~500 tickers)
        mock_sp500_tickers = [f"TICK{i}" for i in range(500)]
        mock_get_sp500.return_value = mock_sp500_tickers

        result = resolve_tickers(["SP500"], mock_logger)

        assert len(result) == 500
        assert "TICK0" in result
        assert "TICK499" in result

    def test_resolve_influx_registry(self, mock_influx_client, mock_logger):
        """Test resolving influx-registry to fetch all InfluxDB tickers."""
        # Mock InfluxDB query response
        mock_df = pd.DataFrame({"ticker": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]})
        mock_influx_client["instance"].query.return_value = mock_df

        result = resolve_tickers(["influx-registry"], mock_logger)

        assert len(result) == 5
        assert "AAPL" in result
        assert "MSFT" in result
        assert "GOOGL" in result
        assert "AMZN" in result
        assert "NVDA" in result

        # Verify InfluxDB client was created with correct database
        mock_influx_client["class"].assert_called_once_with(database="algo-trader-ohlcv")
        mock_influx_client["instance"].query.assert_called_once_with(
            "SELECT DISTINCT ticker FROM ohlcv"
        )
        mock_influx_client["instance"].close.assert_called_once()

        # Verify logging
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("influx-registry specified" in msg for msg in info_calls)
        assert any("Retrieved 5 tickers" in msg for msg in info_calls)

    def test_resolve_influx_registry_empty_result(self, mock_influx_client, mock_logger):
        """Test influx-registry when InfluxDB returns empty result."""
        mock_influx_client["instance"].query.return_value = pd.DataFrame()

        with pytest.raises(
            ValueError, match="Failed to retrieve tickers from InfluxDB OHLCV database"
        ):
            resolve_tickers(["influx-registry"], mock_logger)

        mock_logger.error.assert_called_once()

    def test_resolve_influx_registry_query_failure(self, mock_influx_client, mock_logger):
        """Test influx-registry when InfluxDB query fails."""
        mock_influx_client["instance"].query.return_value = None

        with pytest.raises(
            ValueError, match="Failed to retrieve tickers from InfluxDB OHLCV database"
        ):
            resolve_tickers(["influx-registry"], mock_logger)

        mock_logger.error.assert_called_once()

    def test_resolve_influx_registry_exception(self, mock_influx_client, mock_logger):
        """Test influx-registry when InfluxDB client raises exception."""
        mock_influx_client["class"].side_effect = Exception("Connection error")

        with pytest.raises(
            ValueError, match="Failed to retrieve tickers from InfluxDB OHLCV database"
        ):
            resolve_tickers(["influx-registry"], mock_logger)

        mock_logger.error.assert_called_once()

    def test_resolve_influx_registry_large_dataset(self, mock_influx_client, mock_logger):
        """Test influx-registry with large number of tickers."""
        # Generate mock tickers
        mock_tickers = [f"TICK{i}" for i in range(1000)]
        mock_df = pd.DataFrame({"ticker": mock_tickers})
        mock_influx_client["instance"].query.return_value = mock_df

        result = resolve_tickers(["influx-registry"], mock_logger)

        assert len(result) == 1000
        assert "TICK0" in result
        assert "TICK999" in result
        # Verify sorted
        assert result == sorted(result)

    def test_get_influxdb_tickers_success(self, mock_influx_client):
        """Test get_influxdb_tickers with successful query."""
        mock_df = pd.DataFrame({"ticker": ["AAPL", "MSFT", "GOOGL"]})
        mock_influx_client["instance"].query.return_value = mock_df

        result = get_influxdb_tickers()

        assert len(result) == 3
        assert "AAPL" in result
        assert "MSFT" in result
        assert "GOOGL" in result
        # Verify sorted
        assert result == sorted(result)
        mock_influx_client["instance"].close.assert_called_once()

    def test_get_influxdb_tickers_empty_result(self, mock_influx_client):
        """Test get_influxdb_tickers with empty DataFrame."""
        mock_influx_client["instance"].query.return_value = pd.DataFrame()

        result = get_influxdb_tickers()

        assert result == []
        mock_influx_client["instance"].close.assert_called_once()

    def test_get_influxdb_tickers_none_result(self, mock_influx_client):
        """Test get_influxdb_tickers when query returns None."""
        mock_influx_client["instance"].query.return_value = None

        result = get_influxdb_tickers()

        assert result == []
        mock_influx_client["instance"].close.assert_called_once()

    def test_get_influxdb_tickers_missing_column(self, mock_influx_client):
        """Test get_influxdb_tickers when DataFrame missing ticker column."""
        mock_influx_client["instance"].query.return_value = pd.DataFrame(
            {"other_column": ["value1", "value2"]}
        )

        result = get_influxdb_tickers()

        assert result == []
        mock_influx_client["instance"].close.assert_called_once()

    def test_get_influxdb_tickers_exception(self, mock_influx_client):
        """Test get_influxdb_tickers when exception occurs."""
        mock_influx_client["class"].side_effect = Exception("Connection error")

        result = get_influxdb_tickers()

        assert result == []


class TestFormatSignalSummary:
    """Test signal summary formatting."""

    def test_format_empty_signals(self):
        """Test formatting empty signals DataFrame."""
        empty_signals = pd.DataFrame()

        result = format_signal_summary(empty_signals)

        assert result == "No signals generated"

    def test_format_signals_with_buy_and_sell(self, sample_signals):
        """Test formatting signals with both buy and sell signals."""
        result = format_signal_summary(sample_signals)

        assert "Generated 4 trading signals" in result
        assert "2 BUY signals" in result
        assert "2 SELL signals" in result
        assert "=" * 80 in result

    def test_format_signals_only_buy(self):
        """Test formatting with only buy signals."""
        buy_signals = pd.DataFrame(
            {
                "signal_type": ["buy", "buy", "buy"],
                "price": [100.0, 105.0, 110.0],
            }
        )

        result = format_signal_summary(buy_signals)

        assert "Generated 3 trading signals" in result
        assert "3 BUY signals" in result
        assert "0 SELL signals" in result

    def test_format_signals_only_sell(self):
        """Test formatting with only sell signals."""
        sell_signals = pd.DataFrame(
            {
                "signal_type": ["sell", "sell"],
                "price": [100.0, 105.0],
            }
        )

        result = format_signal_summary(sell_signals)

        assert "Generated 2 trading signals" in result
        assert "0 BUY signals" in result
        assert "2 SELL signals" in result

    def test_format_signals_single_signal(self):
        """Test formatting with single signal."""
        single_signal = pd.DataFrame(
            {
                "signal_type": ["buy"],
                "price": [100.0],
            }
        )

        result = format_signal_summary(single_signal)

        assert "Generated 1 trading signals" in result
        assert "1 BUY signals" in result
        assert "0 SELL signals" in result

    def test_format_signals_output_structure(self, sample_signals):
        """Test that output has proper structure with separators."""
        result = format_signal_summary(sample_signals)

        lines = result.split("\n")

        # Should have header separator
        assert any("=" * 80 in line for line in lines)

        # Should have newlines for readability
        assert lines[0] == ""
        assert lines[-1] == ""


class TestFormatJournalSummary:
    """Test journal summary formatting."""

    def test_format_journal_summary_standard(self):
        """Test formatting standard journal metrics."""
        metrics = {
            "total_trades": 10,
            "total_profit": 1500.50,
            "total_profit_pct": 15.01,
            "max_drawdown": -5.25,
            "sharpe_ratio": 2.35,
        }

        result = format_journal_summary(metrics, "AAPL", "sma-crossover")

        assert "Trading Journal Summary: AAPL - sma-crossover" in result
        assert "Total Trades:      10" in result
        assert "$1500.50" in result
        assert "15.01%" in result
        assert "-5.25%" in result
        # Note: sharpe_ratio is not displayed in format_journal_summary output

    def test_format_journal_summary_zero_trades(self):
        """Test formatting with zero trades."""
        metrics = {
            "total_trades": 0,
            "total_profit": 0.0,
            "total_profit_pct": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
        }

        result = format_journal_summary(metrics, "MSFT", "sma-crossover")

        assert "Total Trades:      0" in result
        assert "$0.00" in result
        assert "0.00%" in result

    def test_format_journal_summary_negative_profit(self):
        """Test formatting with negative profit."""
        metrics = {
            "total_trades": 5,
            "total_profit": -250.75,
            "total_profit_pct": -2.51,
            "max_drawdown": -10.5,
            "sharpe_ratio": -0.5,
        }

        result = format_journal_summary(metrics, "GOOGL", "strategy-name")

        assert "$-250.75" in result
        assert "-2.51%" in result
        assert "-10.50%" in result  # Format shows 2 decimal places
        # Note: sharpe_ratio is not displayed in format_journal_summary output

    def test_format_journal_summary_high_values(self):
        """Test formatting with large numbers."""
        metrics = {
            "total_trades": 1000,
            "total_profit": 1000000.99,
            "total_profit_pct": 100.0,
            "max_drawdown": -50.0,
            "sharpe_ratio": 10.5,
        }

        result = format_journal_summary(metrics, "BRK.A", "test-strategy")

        assert "1000" in result
        assert "$1000000.99" in result
        assert "100.00%" in result

    def test_format_journal_summary_structure(self):
        """Test output structure with separators."""
        metrics = {
            "total_trades": 5,
            "total_profit": 100.0,
            "total_profit_pct": 1.0,
            "max_drawdown": -1.0,
            "sharpe_ratio": 1.0,
        }

        result = format_journal_summary(metrics, "AAPL", "test")

        lines = result.split("\n")

        # Should have separators
        assert any("=" * 80 in line for line in lines)

        # Should start and end with newlines
        assert lines[0] == ""
        assert lines[-1] == ""


class TestFormatTradeDetails:
    """Test detailed trade history formatting."""

    def test_format_empty_trades(self):
        """Test formatting empty trades DataFrame."""
        empty_trades = pd.DataFrame()

        result = format_trade_details(empty_trades)

        assert result == "No completed trades to display"

    def test_format_trade_details_standard(self, sample_trades):
        """Test formatting standard trade details."""
        result = format_trade_details(sample_trades)

        assert "Detailed Trade History" in result
        assert "ENTRY DATE" in result
        assert "ENTRY TIME" in result
        assert "EXIT DATE" in result
        assert "EXIT TIME" in result
        assert "ENTRY" in result
        assert "EXIT" in result
        assert "RETURN $" in result
        assert "RETURN %" in result

        # Check data is present
        assert "2024-01-01" in result
        assert "150.00" in result
        assert "155.00" in result
        assert "500.00" in result
        assert "3.33" in result and "%" in result  # Format has spaces: "3.33      %"

    def test_format_trade_details_negative_pnl(self):
        """Test formatting trade with negative P&L."""
        trades = pd.DataFrame(
            {
                "entry_time": [datetime(2024, 1, 5, 11, 0, 0)],
                "exit_time": [datetime(2024, 1, 8, 14, 0, 0)],
                "entry_price": [155.0],
                "exit_price": [152.0],
                "gross_pnl": [-300.0],
                "gross_pnl_pct": [-1.94],
            }
        )

        trades["shares"] = [100.0]  # Required column
        result = format_trade_details(trades)

        assert "-300.00" in result
        assert "-1.94" in result and "%" in result  # Format has spaces: "-1.94     %"

    def test_format_trade_details_single_trade(self):
        """Test formatting single trade."""
        single_trade = pd.DataFrame(
            {
                "entry_time": [datetime(2024, 1, 1, 10, 0, 0)],
                "exit_time": [datetime(2024, 1, 3, 15, 0, 0)],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
                "gross_pnl_pct": [5.0],
            }
        )

        single_trade["shares"] = [100.0]  # Required column
        result = format_trade_details(single_trade)

        assert "100.00" in result
        assert "105.00" in result
        assert "500.00" in result
        assert "5.00" in result and "%" in result  # Format has spaces: "5.00      %"

    def test_format_trade_details_multiple_trades(self, sample_trades):
        """Test formatting multiple trades."""
        result = format_trade_details(sample_trades)

        # Check all three trades are present
        assert "500.00" in result  # First trade
        assert "-300.00" in result  # Second trade
        assert "800.00" in result  # Third trade

    def test_format_trade_details_structure(self, sample_trades):
        """Test output structure with separators and headers."""
        result = format_trade_details(sample_trades)

        lines = result.split("\n")

        # Should have separators (format uses 120 chars, not 80)
        assert any("=" * 120 in line for line in lines)
        assert any("-" * 120 in line for line in lines)

        # Should have newlines
        assert lines[0] == ""
        assert lines[-1] == ""

    def test_format_trade_details_date_formatting(self):
        """Test that dates are formatted correctly."""
        trades = pd.DataFrame(
            {
                "entry_time": [datetime(2024, 12, 25, 9, 30, 15)],
                "exit_time": [datetime(2024, 12, 31, 16, 0, 45)],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "gross_pnl": [500.0],
                "gross_pnl_pct": [5.0],
            }
        )

        trades["shares"] = [100.0]  # Required column
        result = format_trade_details(trades)

        # Check timestamp format includes date and time separately
        assert "2024-12-25" in result
        assert "09:30:15" in result
        assert "2024-12-31" in result
        assert "16:00:45" in result

    def test_format_trade_details_price_precision(self):
        """Test that prices are formatted with 2 decimal places."""
        trades = pd.DataFrame(
            {
                "entry_time": [datetime(2024, 1, 1, 10, 0, 0)],
                "exit_time": [datetime(2024, 1, 3, 15, 0, 0)],
                "entry_price": [100.123456],
                "exit_price": [105.987654],
                "gross_pnl": [500.555555],
                "gross_pnl_pct": [5.123456],
            }
        )

        trades["shares"] = [100.0]  # Required column
        result = format_trade_details(trades)

        # Check prices are rounded to 2 decimals
        assert "100.12" in result
        assert "105.99" in result
        assert "500.56" in result
        assert "5.12" in result and "%" in result  # Format has spaces: "5.12      %"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_resolve_tickers_empty_list(self, mock_logger):
        """Test resolving empty ticker list."""
        result = resolve_tickers([], mock_logger)

        assert result == []

    def test_format_signal_summary_with_unexpected_signal_type(self):
        """Test formatting with unexpected signal types."""
        signals = pd.DataFrame(
            {
                "signal_type": ["buy", "sell", "hold", "unknown"],
                "price": [100.0, 105.0, 102.0, 103.0],
            }
        )

        result = format_signal_summary(signals)

        # Should still count correctly (hold and unknown won't be counted as buy/sell)
        assert "Generated 4 trading signals" in result
        assert "1 BUY signals" in result
        assert "1 SELL signals" in result

    def test_format_trade_details_with_zero_pnl(self):
        """Test formatting trade with zero P&L."""
        trades = pd.DataFrame(
            {
                "entry_time": [datetime(2024, 1, 1, 10, 0, 0)],
                "exit_time": [datetime(2024, 1, 3, 15, 0, 0)],
                "entry_price": [100.0],
                "exit_price": [100.0],
                "gross_pnl": [0.0],
                "gross_pnl_pct": [0.0],
            }
        )

        trades["shares"] = [100.0]  # Required column
        result = format_trade_details(trades)

        assert "0.00" in result
        assert "0.00" in result and "%" in result  # Format has spaces: "0.00      %"
