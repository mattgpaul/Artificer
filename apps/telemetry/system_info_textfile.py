#!/usr/bin/env python3
"""Host system identity metrics for node_exporter textfile collector.

This is intentionally small and opinionated for the telemetry dashboard:
- CPU model name (from /proc/cpuinfo)
- Display user (from env TELEMETRY_USER, else best-effort via /etc/passwd)
- Primary IPv4 address for the default-route interface (auto-detected)
- Primary network throughput/byte counters for that interface (best-effort)

Emits (labels hold the display strings):
- node_textfile_system_cpu_model{model="..."} 1
- node_textfile_system_user{user="..."} 1
- node_textfile_primary_ipv4{device="wlp13s0",address="192.168.1.10"} 1
- node_textfile_primary_network_receive_bps{device="wlp13s0"} 1234
- node_textfile_primary_network_transmit_bps{device="wlp13s0"} 456
- node_textfile_primary_network_receive_bytes_total{device="wlp13s0"} 123456789
- node_textfile_primary_network_transmit_bytes_total{device="wlp13s0"} 987654321
"""

from __future__ import annotations

import argparse
import fcntl
import os
import re
import socket
import struct
import time
from dataclasses import dataclass
from pathlib import Path


def _escape_label_value(value: str) -> str:
    """Escape a Prometheus label value for text exposition format."""
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _format_sample(metric: str, labels: dict[str, str], value: str) -> str:
    label_items = [f'{k}="{_escape_label_value(v)}"' for k, v in labels.items()]
    return f"{metric}{{{','.join(label_items)}}} {value}"


def write_atomically(output_path: Path, content: str) -> None:
    """Write content to output_path atomically (write temp, then replace)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, output_path)


def read_cpu_model(proc_root: Path) -> str | None:
    """Read CPU model string from procfs."""
    cpuinfo = proc_root / "cpuinfo"
    try:
        text = cpuinfo.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if line.lower().startswith("model name"):
            _, v = line.split(":", 1)
            model = v.strip()
            model = re.sub(r"\s+8-Core Processor\s*$", "", model)
            model = re.sub(r"\s+", " ", model)
            return model
    return None


def read_default_route_iface(proc_root: Path) -> str | None:
    """Best-effort default-route interface from procfs (excluding loopback)."""
    route = proc_root / "net" / "route"
    try:
        lines = route.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if len(lines) <= 1:
        return None
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        iface, dest = parts[0], parts[1]
        if dest == "00000000" and iface != "lo":
            return iface
    return None


def read_iface_ipv4(iface: str) -> str | None:
    """Return IPv4 address for iface using SIOCGIFADDR (host net namespace required)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ifreq = struct.pack("256s", iface.encode("utf-8")[:15])
        res = fcntl.ioctl(s.fileno(), 0x8915, ifreq)  # SIOCGIFADDR
        return socket.inet_ntoa(res[20:24])
    except OSError:
        return None
    finally:
        s.close()


def read_netdev_bytes(proc_root: Path, iface: str) -> tuple[int, int] | None:
    """Return (rx_bytes, tx_bytes) for iface from /proc/net/dev."""
    path = proc_root / "net" / "dev"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        if name.strip() != iface:
            continue
        parts = rest.split()
        # Format: rx_bytes rx_packets ... | tx_bytes tx_packets ...
        if len(parts) < 16:
            return None
        try:
            rx_bytes = int(parts[0])
            tx_bytes = int(parts[8])
        except ValueError:
            return None
        return rx_bytes, tx_bytes
    return None


def _detect_primary_user_from_passwd() -> str | None:
    """Best-effort: pick the first human user (uid >= 1000) from /etc/passwd."""
    passwd_paths = [Path("/host/etc/passwd"), Path("/etc/passwd")]
    for path in passwd_paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        candidates: list[tuple[int, str]] = []
        for line in text.splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) < 3:
                continue
            name = parts[0]
            try:
                uid = int(parts[2])
            except ValueError:
                continue
            if uid >= 1000 and name not in {"nobody"}:
                candidates.append((uid, name))
        if candidates:
            candidates.sort(key=lambda t: t[0])
            return candidates[0][1]
    return None


@dataclass(frozen=False)
class _PrevNet:
    rx_bytes: int | None = None
    tx_bytes: int | None = None
    ts: float | None = None


@dataclass(frozen=True)
class Snapshot:
    """One snapshot of host identity + primary network stats."""

    cpu_model: str | None
    user: str
    iface: str | None
    ip: str | None
    rx_bps: float | None
    tx_bps: float | None
    rx_total: int | None
    tx_total: int | None


def _collect_snapshot(proc_root: Path, user: str, prev: _PrevNet) -> Snapshot:
    cpu_model = read_cpu_model(proc_root)
    iface = read_default_route_iface(proc_root)
    ip = read_iface_ipv4(iface) if iface else None

    rx_bps: float | None = None
    tx_bps: float | None = None
    rx_total: int | None = None
    tx_total: int | None = None

    now = time.monotonic()
    if iface:
        totals = read_netdev_bytes(proc_root, iface)
        if totals is not None:
            rx_total, tx_total = totals
            if prev.rx_bytes is not None and prev.tx_bytes is not None and prev.ts is not None:
                dt = max(0.001, now - prev.ts)
                rx_bps = max(0.0, (rx_total - prev.rx_bytes) / dt)
                tx_bps = max(0.0, (tx_total - prev.tx_bytes) / dt)
            prev.rx_bytes, prev.tx_bytes, prev.ts = rx_total, tx_total, now

    return Snapshot(
        cpu_model=cpu_model,
        user=user,
        iface=iface,
        ip=ip,
        rx_bps=rx_bps,
        tx_bps=tx_bps,
        rx_total=rx_total,
        tx_total=tx_total,
    )


def render(snapshot: Snapshot) -> str:
    """Render Prometheus textfile output for a single snapshot."""
    lines: list[str] = []

    lines.append("# HELP node_textfile_system_cpu_model CPU model name (from /proc/cpuinfo).")
    lines.append("# TYPE node_textfile_system_cpu_model gauge")
    if snapshot.cpu_model:
        lines.append(
            _format_sample("node_textfile_system_cpu_model", {"model": snapshot.cpu_model}, "1")
        )

    lines.append("# HELP node_textfile_system_user Display user for dashboard.")
    lines.append("# TYPE node_textfile_system_user gauge")
    lines.append(_format_sample("node_textfile_system_user", {"user": snapshot.user}, "1"))

    lines.append("# HELP node_textfile_primary_ipv4 Primary IPv4 for default route interface.")
    lines.append("# TYPE node_textfile_primary_ipv4 gauge")
    if snapshot.iface and snapshot.ip:
        lines.append(
            _format_sample(
                "node_textfile_primary_ipv4",
                {"device": snapshot.iface, "address": snapshot.ip},
                "1",
            )
        )

    lines.append(
        "# HELP node_textfile_primary_network_receive_bps Primary iface receive bytes/sec."
    )
    lines.append("# TYPE node_textfile_primary_network_receive_bps gauge")
    if snapshot.iface and snapshot.rx_bps is not None:
        lines.append(
            _format_sample(
                "node_textfile_primary_network_receive_bps",
                {"device": snapshot.iface},
                f"{snapshot.rx_bps:g}",
            )
        )

    lines.append(
        "# HELP node_textfile_primary_network_transmit_bps Primary iface transmit bytes/sec."
    )
    lines.append("# TYPE node_textfile_primary_network_transmit_bps gauge")
    if snapshot.iface and snapshot.tx_bps is not None:
        lines.append(
            _format_sample(
                "node_textfile_primary_network_transmit_bps",
                {"device": snapshot.iface},
                f"{snapshot.tx_bps:g}",
            )
        )

    lines.append(
        "# HELP node_textfile_primary_network_receive_bytes_total "
        "Primary iface receive bytes total."
    )
    lines.append("# TYPE node_textfile_primary_network_receive_bytes_total counter")
    if snapshot.iface and snapshot.rx_total is not None:
        lines.append(
            _format_sample(
                "node_textfile_primary_network_receive_bytes_total",
                {"device": snapshot.iface},
                f"{snapshot.rx_total:d}",
            )
        )

    lines.append(
        "# HELP node_textfile_primary_network_transmit_bytes_total "
        "Primary iface transmit bytes total."
    )
    lines.append("# TYPE node_textfile_primary_network_transmit_bytes_total counter")
    if snapshot.iface and snapshot.tx_total is not None:
        lines.append(
            _format_sample(
                "node_textfile_primary_network_transmit_bytes_total",
                {"device": snapshot.iface},
                f"{snapshot.tx_total:d}",
            )
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    """CLI entrypoint: periodically write host identity + primary network metrics."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--proc-root", default="/host/proc")
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_file = output_dir / "system_info.prom"
    proc_root = Path(args.proc_root)

    user = os.environ.get("TELEMETRY_USER", "").strip() or (
        _detect_primary_user_from_passwd() or "--"
    )

    prev = _PrevNet()
    while True:
        snapshot = _collect_snapshot(proc_root, user, prev)
        write_atomically(output_file, render(snapshot))
        if args.interval_seconds <= 0:
            break
        time.sleep(args.interval_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
