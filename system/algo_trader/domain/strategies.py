"""Trading strategies for algo_trader.

Implements strategy logic including SMA crossover and other technical
indicators.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from system.algo_trader.domain.events import MarketEvent
from system.algo_trader.domain.models import Bar, OrderIntent, Side
from system.algo_trader.ports.portfolio import PortfolioPort
from system.algo_trader.ports.strategy import StrategyPort


def _sma(values: Sequence[Decimal]) -> Decimal:
    return sum(values) / Decimal(len(values))


@dataclass(slots=True)
class SmaCrossoverStrategy(StrategyPort):
    """Simple SMA crossover.

    Uses daily bar closes:
    - If SMA(short) crosses above SMA(long): BUY 1 share
    - If SMA(short) crosses below SMA(long): SELL current position
    """

    window_a: int = 20
    window_b: int = 10

    closes: dict[str, list[Decimal]] = field(default_factory=dict)
    prev_short: dict[str, Decimal | None] = field(default_factory=dict)
    prev_long: dict[str, Decimal | None] = field(default_factory=dict)

    def on_market(self, event: MarketEvent, portfolio: PortfolioPort) -> Sequence[OrderIntent]:
        """Generate order intents based on SMA crossover signals."""
        if event.kind == "bar" and isinstance(event.payload, Bar):
            sym = event.payload.symbol
            price = event.payload.close
        elif (
            event.kind == "quote"
            and hasattr(event.payload, "symbol")
            and hasattr(event.payload, "price")
        ):
            sym = event.payload.symbol
            price = event.payload.price
        else:
            return []

        history = self.closes.setdefault(sym, [])
        history.append(price)

        # Only keep necessary history
        fast = min(self.window_a, self.window_b)
        slow = max(self.window_a, self.window_b)
        if fast <= 0 or slow <= 0:
            raise ValueError("SMA windows must be positive")

        keep = slow + 1
        if len(history) > keep:
            del history[:-keep]

        if len(history) < slow:
            return []

        fast_slice = history[-fast:]
        slow_slice = history[-slow:]

        fast_sma = _sma(fast_slice)
        slow_sma = _sma(slow_slice)

        self.prev_short[sym] = fast_sma
        self.prev_long[sym] = slow_sma

        intents: list[OrderIntent] = []
        pos = getattr(portfolio, "position", lambda _s: Decimal("0"))(sym)

        bullish = fast_sma > slow_sma
        if bullish and pos <= 0:
            intents.append(
                OrderIntent(symbol=sym, side=Side.BUY, qty=Decimal("1"), reason="sma_cross_up")
            )
        elif not bullish and pos > 0:
            intents.append(
                OrderIntent(symbol=sym, side=Side.SELL, qty=pos, reason="sma_cross_down")
            )

        return intents
