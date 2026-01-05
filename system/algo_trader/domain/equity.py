"""Equity tracking utilities for portfolio risk controls.

Equity is defined as:
cash + sum(position_qty[symbol] * latest_price[symbol]).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from system.algo_trader.domain.models import Fill, Side


@dataclass(slots=True)
class EquityTracker:
    """Track cash, positions, and equity curve drawdown."""

    cash: Decimal = Decimal("100000")
    positions_by_symbol: dict[str, Decimal] = field(default_factory=dict)
    avg_cost_by_symbol: dict[str, Decimal] = field(default_factory=dict)
    latest_price_by_symbol: dict[str, Decimal] = field(default_factory=dict)

    peak_equity: Decimal = Decimal("100000")
    last_equity: Decimal = Decimal("100000")

    def update_price(self, symbol: str, price: Decimal) -> None:
        """Update the latest mark price for a symbol."""
        self.latest_price_by_symbol[symbol] = price

    def equity(self) -> Decimal:
        """Return the current marked-to-market equity."""
        total = self.cash
        for sym, qty in self.positions_by_symbol.items():
            px = self.latest_price_by_symbol.get(sym)
            if px is None:
                continue
            total += qty * px
        return total

    def refresh(self) -> Decimal:
        """Recompute equity/peak and return current drawdown fraction."""
        eq = self.equity()
        self.last_equity = eq
        self.peak_equity = max(self.peak_equity, eq)
        if self.peak_equity <= 0:
            return Decimal("0")
        return (self.peak_equity - eq) / self.peak_equity

    def apply_fill(self, fill: Fill) -> Decimal:
        """Apply a fill, returning realized PnL (0 for buys)."""
        qty = fill.qty
        px = fill.price

        if fill.side == Side.BUY:
            self.cash -= qty * px
            cur_qty = self.positions_by_symbol.get(fill.symbol, Decimal("0"))
            cur_cost = self.avg_cost_by_symbol.get(fill.symbol, Decimal("0"))
            new_qty = cur_qty + qty
            if new_qty != 0:
                new_cost = ((cur_qty * cur_cost) + (qty * px)) / new_qty
                self.avg_cost_by_symbol[fill.symbol] = new_cost
            self.positions_by_symbol[fill.symbol] = new_qty
            return Decimal("0")

        # SELL
        self.cash += qty * px
        cur_qty = self.positions_by_symbol.get(fill.symbol, Decimal("0"))
        cur_cost = self.avg_cost_by_symbol.get(fill.symbol, Decimal("0"))
        realized = (px - cur_cost) * qty
        new_qty = cur_qty - qty
        if new_qty == 0:
            self.positions_by_symbol.pop(fill.symbol, None)
            self.avg_cost_by_symbol.pop(fill.symbol, None)
        else:
            self.positions_by_symbol[fill.symbol] = new_qty
        return realized
