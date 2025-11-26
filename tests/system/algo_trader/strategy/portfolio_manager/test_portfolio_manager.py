"""Unit tests for PortfolioManager.

Tests cover portfolio manager application logic, rule pipeline integration,
and capital management. All external dependencies are mocked via conftest.py.
"""

import pandas as pd


class TestPortfolioManager:
    """Test PortfolioManager core functionality."""

    def test_portfolio_manager_keeps_valid_open_and_close(
        self,
        default_portfolio_manager,
        sample_executions,
        make_ohlcv,
    ):
        """Test portfolio manager keeps valid open and close operations."""
        ohlcv = make_ohlcv(["2020-01-01", "2020-01-02", "2020-01-03"])
        approved = default_portfolio_manager.apply(sample_executions, ohlcv)

        assert len(approved) == 2
        assert set(approved["action"]) == {"buy_to_open", "sell_to_close"}

    def test_portfolio_manager_drops_close_without_position(
        self,
        portfolio_manager_insufficient_capital,
        sample_executions_insufficient_capital,
        make_ohlcv,
    ):
        """Test portfolio manager drops close operations without sufficient capital."""
        ohlcv = make_ohlcv(["2020-01-01", "2020-01-02", "2020-01-03"])
        approved = portfolio_manager_insufficient_capital.apply(
            sample_executions_insufficient_capital, ohlcv
        )

        assert approved.empty

    def test_portfolio_manager_empty_executions(self, default_portfolio_manager, make_ohlcv):
        """Test portfolio manager handles empty executions."""
        executions = pd.DataFrame()
        ohlcv = make_ohlcv(["2020-01-01", "2020-01-02", "2020-01-03"])
        approved = default_portfolio_manager.apply(executions, ohlcv)

        assert approved.empty
