from __future__ import annotations

from typing import Protocol

from system.algo_trader.domain.events import OverrideEvent


class OverridePort(Protocol):
    def next_override(self) -> OverrideEvent | None: ...

