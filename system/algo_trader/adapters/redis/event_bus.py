"""Redis Streams event bus adapter for algo_trader."""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from infrastructure.redis.redis import BaseRedisClient
from system.algo_trader.domain.events import DecisionEvent, MarketEvent, OverrideEvent
from system.algo_trader.domain.models import Bar, Quote
from system.algo_trader.ports.data_broker import DataBrokerPort


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _serialize_market(event: MarketEvent) -> dict[str, str]:
    if event.kind == "bar" and isinstance(event.payload, Bar):
        b = event.payload
        return {
            "kind": "bar",
            "symbol": b.symbol,
            "day": b.day.isoformat(),
            "open": str(b.open),
            "high": str(b.high),
            "low": str(b.low),
            "close": str(b.close),
            "volume": str(b.volume),
        }
    if event.kind == "quote" and isinstance(event.payload, Quote):
        q = event.payload
        return {
            "kind": "quote",
            "symbol": q.symbol,
            "ts": q.ts.isoformat(),
            "price": str(q.price),
            "bid": "" if q.bid is None else str(q.bid),
            "ask": "" if q.ask is None else str(q.ask),
            "volume": "" if q.volume is None else str(q.volume),
        }
    return {"kind": "unknown", "payload": json.dumps(event.payload, default=str)}


@dataclass(slots=True)
class AlgoTraderRedisBroker(BaseRedisClient, DataBrokerPort):
    """Redis Streams event bus for algo_trader.

    Streams:
    - `{engine_id}:events:market` (optional fanout / auditing)
    - `{engine_id}:events:decision`
    - `{engine_id}:events:override` (CLI writes; engine consumes)
    """

    engine_id: str = "default"
    consumer_group: str = "algo_trader"
    consumer_name: str = ""

    def __post_init__(self) -> None:
        """Initialize consumer group and name from engine_id."""
        if self.engine_id:
            self.consumer_group = f"algo_trader:{self.engine_id}"
        if not self.consumer_name:
            self.consumer_name = f"{socket.gethostname()}:{os.getpid()}"
        self._ensure_group(self._stream("events:override"), self.consumer_group)

    def _get_namespace(self) -> str:
        return "algo_trader"

    def _stream(self, name: str) -> str:
        return f"{self.engine_id}:{name}"

    def _xadd(self, stream: str, fields: dict[str, str], maxlen: int | None = 10_000) -> str:
        key = self._build_key(stream)
        return self.client.xadd(key, fields, maxlen=maxlen, approximate=True)

    def _ensure_group(self, stream: str, group: str) -> None:
        key = self._build_key(stream)
        try:
            self.client.xgroup_create(key, group, id="0-0", mkstream=True)
        except Exception:
            # Group likely already exists.
            return

    def publish_market(self, events: Sequence[MarketEvent]) -> None:
        """Publish market events to Redis stream."""
        for e in events:
            payload = _serialize_market(e)
            payload["emitted_at"] = _utc_now().isoformat()
            self._xadd(self._stream("events:market"), payload)

    def publish_decision(self, event: DecisionEvent) -> None:
        """Publish decision event to Redis stream."""
        fields = {
            "ts": event.ts.isoformat(),
            "order_intents": json.dumps(
                [
                    {
                        "symbol": i.symbol,
                        "side": i.side.value,
                        "qty": str(i.qty),
                        "reason": i.reason,
                    }
                    for i in event.order_intents
                ]
            ),
        }
        self._xadd(self._stream("events:decision"), fields)

    def publish_override(self, event: OverrideEvent) -> None:
        """Publish override event to Redis stream."""
        fields = {
            "ts": event.ts.isoformat(),
            "command": event.command,
            "args": json.dumps(event.args),
        }
        self._xadd(self._stream("events:override"), fields)

    def poll_overrides(self, max_items: int = 10) -> Sequence[OverrideEvent]:
        """Poll for override events via consumer group."""
        # Consume overrides via consumer group (durable-ish, at-least-once).
        stream_key = self._build_key(self._stream("events:override"))
        resp = self.client.xreadgroup(
            groupname=self.consumer_group,
            consumername=self.consumer_name,
            streams={stream_key: ">"},
            count=max_items,
            block=0,
        )

        events: list[OverrideEvent] = []
        for _stream, messages in resp:
            for msg_id, fields in messages:
                ts = fields.get(b"ts", b"").decode("utf-8") or _utc_now().isoformat()
                command = fields.get(b"command", b"").decode("utf-8")
                args_raw = fields.get(b"args", b"{}").decode("utf-8")
                try:
                    args: dict[str, str] = json.loads(args_raw)
                except Exception:
                    args = {}

                events.append(
                    OverrideEvent(ts=datetime.fromisoformat(ts), command=command, args=args)
                )
                # Ack immediately; overrides are operator-driven and should not replay indefinitely.
                try:
                    self.client.xack(stream_key, self.consumer_group, msg_id)
                except Exception:
                    pass
        return events
