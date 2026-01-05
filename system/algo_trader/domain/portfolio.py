from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from system.algo_trader.domain.events import OverrideEvent
from system.algo_trader.domain.models import Fill, OrderIntent, Side
from system.algo_trader.ports.portfolio import PortfolioPort


@dataclass(slots=True)
class SimplePortfolio(PortfolioPort):
    """Minimal portfolio schema for backtest/forward-test.

    - Tracks positions by symbol
    - Allows CLI overrides to disable symbols or flatten
    """

    max_symbols: int = 200
    positions_by_symbol: dict[str, Decimal] = field(default_factory=dict)
    disabled_symbols: set[str] = field(default_factory=set)

    def position(self, symbol: str) -> Decimal:
        return self.positions_by_symbol.get(symbol, Decimal("0"))

    def validate(self, intents: Sequence[OrderIntent]) -> Sequence[OrderIntent]:
        """Filter/adjust intents based on portfolio rules.

        Currently:
        - Drop intents for disabled symbols
        - Prevent opening new symbols beyond `max_symbols`
        """
        valid: list[OrderIntent] = []
        open_symbols = set(self.positions_by_symbol.keys())
        for intent in intents:
            if intent.symbol in self.disabled_symbols:
                continue
            if intent.side == Side.BUY:
                # If we're not already holding it, this intent would open a new symbol.
                if intent.symbol not in open_symbols and len(open_symbols) >= self.max_symbols:
                    continue
                open_symbols.add(intent.symbol)
            valid.append(intent)
        return valid

    def apply_fill(self, fill: Fill) -> None:
        current = self.position(fill.symbol)
        if fill.side == Side.BUY:
            self.positions_by_symbol[fill.symbol] = current + fill.qty
        else:
            self.positions_by_symbol[fill.symbol] = current - fill.qty

        if self.positions_by_symbol[fill.symbol] == 0:
            self.positions_by_symbol.pop(fill.symbol, None)

    def on_override(self, event: OverrideEvent) -> None:
        cmd = event.command.lower().strip()
        if cmd == "disable_symbol":
            sym = event.args.get("symbol")
            if sym:
                self.disabled_symbols.add(sym)
            return
        if cmd == "enable_symbol":
            sym = event.args.get("symbol")
            if sym:
                self.disabled_symbols.discard(sym)
            return
        if cmd == "flatten":
            # Portfolio-level flatten is handled by app/broker wiring (issue SELL intents).
            return
