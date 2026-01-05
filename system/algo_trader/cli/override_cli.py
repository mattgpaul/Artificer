from __future__ import annotations

import shlex
from datetime import datetime, timezone
from typing import Protocol

from system.algo_trader.adapters.redis.engine_registry import AlgoTraderEngineRegistry
from system.algo_trader.adapters.redis.event_bus import AlgoTraderRedisBroker
from system.algo_trader.adapters.redis.runtime_config import AlgoTraderRuntimeConfigStore
from system.algo_trader.domain.events import OverrideEvent


def _parse(line: str) -> OverrideEvent | None:
    parts = shlex.split(line)
    if not parts:
        return None

    cmd = parts[0].strip()
    args: dict[str, str] = {}

    # Common shorthand forms:
    # - disable_symbol AAPL
    # - enable_symbol AAPL
    if cmd in {"disable_symbol", "enable_symbol"} and len(parts) >= 2:
        args["symbol"] = parts[1].strip().upper()

    # - set_poll_seconds 1.5
    if cmd == "set_poll_seconds" and len(parts) >= 2:
        args["poll_seconds"] = parts[1].strip()

    # Generic key=value args
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            args[k.strip()] = v.strip()

    return OverrideEvent(ts=datetime.now(tz=timezone.utc), command=cmd, args=args)


class _RuntimeConfigPort(Protocol):
    def set_poll_seconds(self, engine_id: str, poll_seconds: float, ttl_seconds: int | None = None) -> None: ...


def apply_runtime_side_effects(engine_id: str, event: OverrideEvent, runtime: _RuntimeConfigPort) -> None:
    """Apply non-event side effects for specific overrides (KV updates)."""
    if event.command.lower().strip() == "set_poll_seconds":
        raw = event.args.get("poll_seconds", "")
        runtime.set_poll_seconds(engine_id, float(raw))


def _select_engine_id(registry: AlgoTraderEngineRegistry) -> str:
    engines = registry.list_engines()
    if not engines:
        raise RuntimeError("No engines registered in Redis (algo_trader:engines is empty).")
    if len(engines) == 1:
        return engines[0]

    print("Select engine_id:")
    for i, eid in enumerate(engines, start=1):
        status = registry.get_status(eid) or {}
        mode = status.get("mode", "")
        ts = status.get("ts", "")
        suffix = " ".join([x for x in [mode, ts] if x])
        print(f"{i}) {eid} {suffix}".rstrip())
    while True:
        choice = input("> ").strip()
        try:
            idx = int(choice)
        except Exception:
            idx = 0
        if 1 <= idx <= len(engines):
            return engines[idx - 1]
        print("Enter a valid number.")


def main() -> None:
    registry = AlgoTraderEngineRegistry()
    engine_id = _select_engine_id(registry)
    broker = AlgoTraderRedisBroker(engine_id=engine_id)
    runtime = AlgoTraderRuntimeConfigStore()

    print("algo_trader override CLI")
    print(f"engine_id={engine_id}")
    print(
        "Commands: pause | resume | flatten | disable_symbol <SYM> | enable_symbol <SYM> | "
        "set_poll_seconds <SECONDS> | quit"
    )
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break

        if not line:
            continue
        if line.lower() in {"q", "quit", "exit"}:
            break

        event = _parse(line)
        if event is None:
            continue

        try:
            apply_runtime_side_effects(engine_id, event, runtime)
        except Exception as e:
            print(f"failed to apply override side effects: {e}")
            continue

        broker.publish_override(event)
        print(f"published override: {event.command} {event.args}")


if __name__ == "__main__":
    main()
