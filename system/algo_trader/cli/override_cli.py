from __future__ import annotations

import shlex
from datetime import datetime, timezone

from system.algo_trader.adapters.redis.event_bus import AlgoTraderRedisBroker
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

    # Generic key=value args
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            args[k.strip()] = v.strip()

    return OverrideEvent(ts=datetime.now(tz=timezone.utc), command=cmd, args=args)


def main() -> None:
    broker = AlgoTraderRedisBroker()

    print("algo_trader override CLI")
    print("Commands: pause | resume | flatten | disable_symbol <SYM> | enable_symbol <SYM> | quit")
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

        broker.publish_override(event)
        print(f"published override: {event.command} {event.args}")


if __name__ == "__main__":
    main()

