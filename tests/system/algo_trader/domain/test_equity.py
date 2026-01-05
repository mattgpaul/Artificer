"""Unit tests for EquityTracker - Equity curve tracking.

Tests cover:
- Price updates and equity calculation
- Peak equity tracking and drawdown computation
- Fill processing (BUY/SELL) with average cost tracking
- Realized PnL calculation

All operations are deterministic with no external dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from system.algo_trader.domain.equity import EquityTracker
from system.algo_trader.domain.models import Fill, Side


class TestEquityTracker:
    """Test EquityTracker core functionality."""

    def test_initialization_defaults(self):
        """Test EquityTracker initializes with $100k cash."""
        tracker = EquityTracker()
        assert tracker.cash == Decimal("100000")
        assert tracker.peak_equity == Decimal("100000")
        assert tracker.last_equity == Decimal("100000")
        assert tracker.equity() == Decimal("100000")

    def test_update_price_stores_latest_price(self):
        """Test update_price stores symbol price."""
        tracker = EquityTracker()
        tracker.update_price("AAPL", Decimal("150"))
        assert tracker.latest_price_by_symbol["AAPL"] == Decimal("150")

    def test_equity_without_positions_equals_cash(self):
        """Test equity equals cash when no positions."""
        tracker = EquityTracker(cash=Decimal("50000"))
        assert tracker.equity() == Decimal("50000")

    def test_equity_with_positions_includes_marked_value(self):
        """Test equity includes marked-to-market position value."""
        tracker = EquityTracker(cash=Decimal("50000"))
        tracker.positions_by_symbol["AAPL"] = Decimal("100")
        tracker.update_price("AAPL", Decimal("150"))
        assert tracker.equity() == Decimal("65000")  # 50k + 100 * 150

    def test_equity_ignores_positions_without_price(self):
        """Test equity ignores positions without latest price."""
        tracker = EquityTracker(cash=Decimal("50000"))
        tracker.positions_by_symbol["AAPL"] = Decimal("100")
        # No price update
        assert tracker.equity() == Decimal("50000")

    def test_refresh_updates_peak_equity_when_higher(self):
        """Test refresh updates peak when equity exceeds previous peak."""
        tracker = EquityTracker(cash=Decimal("100000"))
        tracker.positions_by_symbol["AAPL"] = Decimal("100")
        tracker.update_price("AAPL", Decimal("200"))
        dd = tracker.refresh()
        assert tracker.peak_equity == Decimal("120000")
        assert tracker.last_equity == Decimal("120000")
        assert dd == Decimal("0")

    def test_refresh_calculates_drawdown_when_below_peak(self):
        """Test refresh calculates drawdown fraction when equity drops."""
        tracker = EquityTracker(cash=Decimal("100000"))
        tracker.peak_equity = Decimal("120000")
        tracker.positions_by_symbol["AAPL"] = Decimal("100")
        tracker.update_price("AAPL", Decimal("100"))  # Equity = 110k
        dd = tracker.refresh()
        assert tracker.last_equity == Decimal("110000")
        assert tracker.peak_equity == Decimal("120000")  # Unchanged
        expected = (Decimal("120000") - Decimal("110000")) / Decimal("120000")
        assert dd == expected  # (120k - 110k) / 120k

    def test_refresh_handles_zero_peak_equity(self):
        """Test refresh returns 0 drawdown when peak equity is zero."""
        tracker = EquityTracker(cash=Decimal("0"))
        tracker.peak_equity = Decimal("0")
        dd = tracker.refresh()
        assert dd == Decimal("0")

    @pytest.mark.parametrize(
        "cash,price,qty,expected_cash",
        [
            (Decimal("100000"), Decimal("100"), Decimal("10"), Decimal("99000")),
            (Decimal("50000"), Decimal("50"), Decimal("5"), Decimal("49750")),
        ],
    )
    def test_apply_fill_buy_reduces_cash(self, cash, price, qty, expected_cash):
        """Test BUY fill reduces cash by qty * price."""
        tracker = EquityTracker(cash=cash)
        fill = Fill(
            symbol="AAPL",
            side=Side.BUY,
            qty=qty,
            price=price,
            ts=datetime.now(tz=timezone.utc),
        )
        realized = tracker.apply_fill(fill)
        assert tracker.cash == expected_cash
        assert realized == Decimal("0")

    def test_apply_fill_buy_new_position_sets_avg_cost(self):
        """Test BUY fill for new position sets average cost."""
        tracker = EquityTracker()
        fill = Fill(
            symbol="AAPL",
            side=Side.BUY,
            qty=Decimal("10"),
            price=Decimal("100"),
            ts=datetime.now(tz=timezone.utc),
        )
        tracker.apply_fill(fill)
        assert tracker.positions_by_symbol["AAPL"] == Decimal("10")
        assert tracker.avg_cost_by_symbol["AAPL"] == Decimal("100")

    def test_apply_fill_buy_adds_to_existing_calculates_weighted_avg(self):
        """Test BUY fill adds to existing position with weighted average cost."""
        tracker = EquityTracker()
        tracker.positions_by_symbol["AAPL"] = Decimal("10")
        tracker.avg_cost_by_symbol["AAPL"] = Decimal("100")
        fill = Fill(
            symbol="AAPL",
            side=Side.BUY,
            qty=Decimal("10"),
            price=Decimal("120"),
            ts=datetime.now(tz=timezone.utc),
        )
        tracker.apply_fill(fill)
        assert tracker.positions_by_symbol["AAPL"] == Decimal("20")
        assert tracker.avg_cost_by_symbol["AAPL"] == Decimal("110")  # (10*100 + 10*120) / 20

    def test_apply_fill_sell_increases_cash(self):
        """Test SELL fill increases cash by qty * price."""
        tracker = EquityTracker(cash=Decimal("100000"))
        tracker.positions_by_symbol["AAPL"] = Decimal("10")
        tracker.avg_cost_by_symbol["AAPL"] = Decimal("100")
        fill = Fill(
            symbol="AAPL",
            side=Side.SELL,
            qty=Decimal("5"),
            price=Decimal("150"),
            ts=datetime.now(tz=timezone.utc),
        )
        realized = tracker.apply_fill(fill)
        assert tracker.cash == Decimal("100750")  # 100k + 5 * 150
        assert realized == Decimal("250")  # (150 - 100) * 5

    def test_apply_fill_sell_calculates_realized_loss(self):
        """Test SELL fill calculates negative realized PnL for loss."""
        tracker = EquityTracker(cash=Decimal("100000"))
        tracker.positions_by_symbol["AAPL"] = Decimal("10")
        tracker.avg_cost_by_symbol["AAPL"] = Decimal("100")
        fill = Fill(
            symbol="AAPL",
            side=Side.SELL,
            qty=Decimal("5"),
            price=Decimal("80"),
            ts=datetime.now(tz=timezone.utc),
        )
        realized = tracker.apply_fill(fill)
        assert realized == Decimal("-100")  # (80 - 100) * 5

    def test_apply_fill_sell_closes_position_when_qty_zero(self):
        """Test SELL fill removes position and avg_cost when qty reaches zero."""
        tracker = EquityTracker()
        tracker.positions_by_symbol["AAPL"] = Decimal("10")
        tracker.avg_cost_by_symbol["AAPL"] = Decimal("100")
        fill = Fill(
            symbol="AAPL",
            side=Side.SELL,
            qty=Decimal("10"),
            price=Decimal("150"),
            ts=datetime.now(tz=timezone.utc),
        )
        tracker.apply_fill(fill)
        assert "AAPL" not in tracker.positions_by_symbol
        assert "AAPL" not in tracker.avg_cost_by_symbol
