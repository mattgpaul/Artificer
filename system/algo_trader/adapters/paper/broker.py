"""Paper broker adapter for backtests/forward-tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from system.algo_trader.domain.models import Fill, OrderIntent, Side
from system.algo_trader.ports.broker import BrokerPort


@dataclass(slots=True)
class PaperBroker(BrokerPort):
    """In-memory paper broker.

    - `set_price()` must be called to establish execution price for a symbol.
    - Orders fill immediately at latest price.
    """

    prices: dict[str, Decimal] = field(default_factory=dict)
    ts: datetime | None = None
    _fills: list[Fill] = field(default_factory=list)
    _order_seq: int = 0

    def set_price(self, symbol: str, price: Decimal, ts: datetime) -> None:
        """Set the latest execution price for a symbol."""
        self.prices[symbol] = price
        self.ts = ts

    def place_orders(self, intents: Sequence[OrderIntent]) -> Sequence[str]:
        """Place orders and queue immediate fills at the latest known price."""
        ids: list[str] = []
        for intent in intents:
            self._order_seq += 1
            order_id = f"paper-{self._order_seq}"
            ids.append(order_id)

            price = self.prices.get(intent.symbol)
            if price is None:
                # No price -> cannot fill.
                continue
            ts = self.ts or datetime.utcnow()

            self._fills.append(
                Fill(
                    symbol=intent.symbol,
                    side=Side.BUY if intent.side == Side.BUY else Side.SELL,
                    qty=intent.qty,
                    price=price,
                    ts=ts,
                )
            )
        return ids

    def poll_fills(self) -> Sequence[Fill]:
        """Return and clear any queued fills."""
        fills = list(self._fills)
        self._fills.clear()
        return fills
