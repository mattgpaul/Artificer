from __future__ import annotations

from typing import Protocol, Sequence

from system.algo_trader.domain.models import Fill, OrderIntent


class BrokerPort(Protocol):
    def place_orders(self, intents: Sequence[OrderIntent]) -> Sequence[str]:
        """Return broker-specific order IDs."""

    def poll_fills(self) -> Sequence[Fill]:
        """Return any new fills since last poll."""

