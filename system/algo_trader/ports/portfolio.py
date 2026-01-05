from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from system.algo_trader.domain.events import OverrideEvent
from system.algo_trader.domain.models import Fill, OrderIntent


class PortfolioPort(Protocol):
    def validate(self, intents: Sequence[OrderIntent]) -> Sequence[OrderIntent]: ...

    def apply_fill(self, fill: Fill) -> None: ...

    def on_override(self, event: OverrideEvent) -> None: ...
