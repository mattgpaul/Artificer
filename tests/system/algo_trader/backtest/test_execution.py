"""Unit tests for ExecutionSimulator.

Tests cover execution simulation, fill price calculation, and slippage/commission handling.
"""

import pandas as pd

from system.algo_trader.backtest.execution import ExecutionConfig, ExecutionSimulator


class TestExecutionConfig:
    """Test ExecutionConfig dataclass."""

    def test_default_values(self):
        """Test ExecutionConfig default values."""
        config = ExecutionConfig()
        assert config.slippage_bps == 5.0
        assert config.commission_per_share == 0.005
        assert config.use_limit_orders is False
        assert config.fill_delay_minutes == 0

    def test_custom_values(self):
        """Test ExecutionConfig with custom values."""
        config = ExecutionConfig(
            slippage_bps=10.0,
            commission_per_share=0.01,
            use_limit_orders=True,
            fill_delay_minutes=5,
        )
        assert config.slippage_bps == 10.0
        assert config.commission_per_share == 0.01
        assert config.use_limit_orders is True
        assert config.fill_delay_minutes == 5


class TestExecutionSimulator:
    """Test ExecutionSimulator operations."""

    def test_initialization(self, execution_config):
        """Test ExecutionSimulator initialization."""
        simulator = ExecutionSimulator(execution_config)
        assert simulator.config == execution_config

    def test_apply_execution_empty_trades(self, execution_config):
        """Test apply_execution with empty trades DataFrame."""
        simulator = ExecutionSimulator(execution_config)
        empty_trades = pd.DataFrame()
        ohlcv_data = {}

        result = simulator.apply_execution(empty_trades, ohlcv_data)
        assert result.empty

    def test_apply_execution_with_ohlcv_data(self, execution_config, sample_ohlcv_data):
        """Test apply_execution with valid trades and OHLCV data."""
        simulator = ExecutionSimulator(execution_config)

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-01", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-02", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [101.0],
                "shares": [100],
                "side": ["LONG"],
            }
        )

        ohlcv_data = {"AAPL": sample_ohlcv_data}

        result = simulator.apply_execution(trades, ohlcv_data)

        assert not result.empty
        assert "gross_pnl" in result.columns
        assert "net_pnl" in result.columns
        assert "commission" in result.columns
        assert "gross_pnl_pct" in result.columns
        assert "net_pnl_pct" in result.columns

    def test_apply_execution_long_side(self, execution_config):
        """Test apply_execution for LONG side trades."""
        simulator = ExecutionSimulator(execution_config)

        # Create OHLCV data where next bar after entry has higher price
        dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0, 102.0, 104.0, 106.0, 108.0],
                "high": [101.0, 103.0, 105.0, 107.0, 109.0],
                "low": [99.0, 101.0, 103.0, 105.0, 107.0],
                "close": [100.5, 102.5, 104.5, 106.5, 108.5],
                "volume": [1000000] * 5,
            },
            index=dates,
        )

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-01", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-03", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [105.0],
                "shares": [100],
                "side": ["LONG"],
            }
        )

        ohlcv_dict = {"AAPL": ohlcv_data}
        result = simulator.apply_execution(trades, ohlcv_dict)

        # For LONG, profit = shares * (exit_fill - entry_fill)
        # With slippage, entry_fill will be higher than entry_price
        # but exit_fill should still result in profit if exit > entry
        assert "gross_pnl" in result.columns
        assert "net_pnl" in result.columns

    def test_apply_execution_short_side(self, execution_config, sample_ohlcv_data):
        """Test apply_execution for SHORT side trades."""
        simulator = ExecutionSimulator(execution_config)

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-01", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-02", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [90.0],
                "shares": [100],
                "side": ["SHORT"],
            }
        )

        ohlcv_data = {"AAPL": sample_ohlcv_data}
        result = simulator.apply_execution(trades, ohlcv_data)

        # For SHORT, profit = shares * (entry - exit)
        assert result.iloc[0]["gross_pnl"] > 0

    def test_apply_execution_commission_calculation(self, execution_config, sample_ohlcv_data):
        """Test commission calculation in apply_execution."""
        config = ExecutionConfig(commission_per_share=0.01)
        simulator = ExecutionSimulator(config)

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-01", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-02", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [101.0],
                "shares": [100],
                "side": ["LONG"],
            }
        )

        ohlcv_data = {"AAPL": sample_ohlcv_data}
        result = simulator.apply_execution(trades, ohlcv_data)

        # Commission = shares * commission_per_share * 2 (entry + exit)
        expected_commission = 100 * 0.01 * 2
        assert result.iloc[0]["commission"] == expected_commission

    def test_apply_execution_net_pnl_calculation(self, execution_config, sample_ohlcv_data):
        """Test net PnL calculation (gross PnL - commission)."""
        simulator = ExecutionSimulator(execution_config)

        trades = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "entry_time": [pd.Timestamp("2024-01-01", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-02", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [101.0],
                "shares": [100],
                "side": ["LONG"],
            }
        )

        ohlcv_data = {"AAPL": sample_ohlcv_data}
        result = simulator.apply_execution(trades, ohlcv_data)

        # Net PnL should be gross PnL - commission
        gross_pnl = result.iloc[0]["gross_pnl"]
        commission = result.iloc[0]["commission"]
        net_pnl = result.iloc[0]["net_pnl"]

        assert net_pnl == gross_pnl - commission

    def test_apply_execution_missing_ticker_data(self, execution_config):
        """Test apply_execution when ticker not in ohlcv_data."""
        simulator = ExecutionSimulator(execution_config)

        trades = pd.DataFrame(
            {
                "ticker": ["UNKNOWN"],
                "entry_time": [pd.Timestamp("2024-01-01", tz="UTC")],
                "exit_time": [pd.Timestamp("2024-01-02", tz="UTC")],
                "entry_price": [100.0],
                "exit_price": [101.0],
                "shares": [100],
                "side": ["LONG"],
            }
        )

        ohlcv_data = {}
        result = simulator.apply_execution(trades, ohlcv_data)

        # Should use signal prices when no OHLCV data available
        assert not result.empty
