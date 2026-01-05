"""TimescaleDB journal adapter for algo_trader events."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from system.algo_trader.adapters.timescale.store import AlgoTraderStore
from system.algo_trader.domain.events import DecisionEvent, OverrideEvent
from system.algo_trader.domain.models import Fill
from system.algo_trader.ports.journal import JournalPort


@dataclass(slots=True)
class TimescaleJournal(JournalPort):
    store: AlgoTraderStore
    run_id: str | None = None

    def record_decision(self, event: DecisionEvent) -> None:
        def _intent(i) -> dict[str, str]:
            out = {
                "symbol": i.symbol,
                "side": i.side.value,
                "qty": str(i.qty),
                "reason": i.reason,
            }
            if i.reference_price is not None:
                out["reference_price"] = str(i.reference_price)
            return out

        payload: dict[str, Any] = {
            # Backwards-compatible field (final intents).
            "order_intents": [_intent(i) for i in event.order_intents],
            "proposed_intents": [_intent(i) for i in event.proposed_intents],
            "final_intents": [_intent(i) for i in event.order_intents],
            "audit": event.audit,
        }
        self.store.db.execute(
            f"""
            INSERT INTO {self.store._schema_q()}.decision_event(ts, run_id, payload)
            VALUES (%s, %s, %s::jsonb)
            """,
            (event.ts, self.run_id, json.dumps(payload)),
        )

    def record_override(self, event: OverrideEvent) -> None:
        self.store.db.execute(
            f"""
            INSERT INTO {self.store._schema_q()}.override_event(ts, run_id, command, args)
            VALUES (%s, %s, %s, %s::jsonb)
            """,
            (event.ts, self.run_id, event.command, json.dumps(event.args)),
        )

    def record_fill(self, fill: Fill) -> None:  # optional extension consumed by Engine
        self.store.record_fill(fill, run_id=self.run_id)
