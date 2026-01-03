#!/usr/bin/env python3
"""Top process metrics for Prometheus node_exporter textfile collector.

This script reads process stats from a procfs mount (typically the host's /proc)
and writes a Prometheus textfile for node_exporter's textfile collector.

It emits only the top-N processes by CPU and RSS memory, similar to the
"top processes" section in Conky.
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from pathlib import Path


def _escape_label_value(value: str) -> str:
    # Prometheus label value escaping for \, ", and newlines.
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


@dataclass(frozen=True)
class ProcSample:
    """A single point-in-time process sample from procfs."""

    pid: int
    comm: str
    cpu_total_seconds: float
    rss_bytes: int


def _read_proc_sample(
    proc_root: Path, pid: int, *, clk_tck: int, page_size: int
) -> ProcSample | None:
    stat_path = proc_root / str(pid) / "stat"
    stat = _read_text(stat_path)
    if not stat:
        return None

    # /proc/<pid>/stat format:
    # pid (comm) state ... utime stime ... rss ...
    # comm can contain spaces and parentheses; extract between first '(' and last ')'.
    lpar = stat.find("(")
    rpar = stat.rfind(")")
    if lpar == -1 or rpar == -1 or rpar <= lpar:
        return None

    comm = stat[lpar + 1 : rpar]
    rest = stat[rpar + 2 :].split()  # after ") "

    # utime is field 14, stime is field 15; in "rest" (starting from field 3)
    # indices: field 3 -> rest[0], so utime (14) -> rest[11], stime (15) -> rest[12]
    try:
        utime_jiffies = int(rest[11])
        stime_jiffies = int(rest[12])
        rss_pages = int(rest[21])  # rss is field 24 -> rest[21]
    except (IndexError, ValueError):
        return None

    cpu_total_seconds = (utime_jiffies + stime_jiffies) / float(clk_tck)
    rss_bytes = max(0, rss_pages) * page_size

    comm_path = proc_root / str(pid) / "comm"
    comm_override = _read_text(comm_path)
    if comm_override:
        comm = comm_override

    return ProcSample(pid=pid, comm=comm, cpu_total_seconds=cpu_total_seconds, rss_bytes=rss_bytes)


def write_atomically(output_path: Path, content: str) -> None:
    """Write the output content to disk atomically (write temp, then replace)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, output_path)


def render(
    *,
    top_cpu: list[tuple[int, ProcSample, float]],
    top_rss: list[tuple[int, ProcSample]],
    mem_total_bytes: int | None,
) -> str:
    """Render Prometheus textfile collector metrics for the given process rankings."""
    lines: list[str] = []

    lines.append(
        "# HELP node_textfile_top_process_cpu_percent "
        "Top processes by CPU usage over the last interval."
    )
    lines.append("# TYPE node_textfile_top_process_cpu_percent gauge")
    for rank, sample, cpu_percent in top_cpu:
        lines.append(
            f'node_textfile_top_process_cpu_percent{{rank="{rank}",pid="{sample.pid}",'
            f'comm="{_escape_label_value(sample.comm)}"}} {cpu_percent:g}'
        )

    lines.append(
        "# HELP node_textfile_top_process_rss_bytes Top processes by resident memory (RSS)."
    )
    lines.append("# TYPE node_textfile_top_process_rss_bytes gauge")
    for rank, sample in top_rss:
        lines.append(
            f'node_textfile_top_process_rss_bytes{{rank="{rank}",pid="{sample.pid}",'
            f'comm="{_escape_label_value(sample.comm)}"}} {sample.rss_bytes:d}'
        )

    if mem_total_bytes and mem_total_bytes > 0:
        lines.append(
            "# HELP node_textfile_top_process_mem_percent "
            "Top processes by RSS as percent of total RAM."
        )
        lines.append("# TYPE node_textfile_top_process_mem_percent gauge")
        for rank, sample in top_rss:
            mem_percent = (sample.rss_bytes / mem_total_bytes) * 100.0
            lines.append(
                f'node_textfile_top_process_mem_percent{{rank="{rank}",pid="{sample.pid}",'
                f'comm="{_escape_label_value(sample.comm)}"}} {mem_percent:g}'
            )

    return "\n".join(lines) + "\n"


def _read_mem_total_bytes(proc_root: Path) -> int | None:
    meminfo = _read_text(proc_root / "meminfo")
    if not meminfo:
        return None
    for line in meminfo.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    # meminfo is in kB.
                    return int(parts[1]) * 1024
                except ValueError:
                    return None
    return None


@dataclass(frozen=True)
class _RunContext:
    proc_root: Path
    output_file: Path
    clk_tck: int
    page_size: int
    top_n: int


@dataclass
class _RunState:
    prev_cpu: dict[int, float]
    prev_ts: float


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for node_exporter textfile collector (mounted volume).",
    )
    parser.add_argument(
        "--proc-root",
        default="/host/proc",
        help="Procfs root to read processes from (default: /host/proc).",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=5.0,
        help="Polling interval. Use 0 to run once and exit.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of processes to emit for each ranking.",
    )
    return parser.parse_args()


def _run_once(
    ctx: _RunContext,
    state: _RunState,
    *,
    interval_seconds: float,
) -> None:
    now_ts = time.monotonic()
    dt = max(0.001, now_ts - state.prev_ts) if interval_seconds > 0 else 0.001

    samples: list[ProcSample] = []
    try:
        for child in ctx.proc_root.iterdir():
            if not child.is_dir():
                continue
            if not child.name.isdigit():
                continue
            pid = int(child.name)
            sample = _read_proc_sample(
                ctx.proc_root,
                pid,
                clk_tck=ctx.clk_tck,
                page_size=ctx.page_size,
            )
            if sample is not None:
                samples.append(sample)
    except OSError:
        samples = []

    top_cpu_scored: list[tuple[int, ProcSample, float]] = []
    for sample in samples:
        prev = state.prev_cpu.get(sample.pid)
        if prev is None:
            continue
        cpu_percent = max(0.0, (sample.cpu_total_seconds - prev) / dt * 100.0)
        top_cpu_scored.append((0, sample, cpu_percent))

    state.prev_cpu = {s.pid: s.cpu_total_seconds for s in samples}
    state.prev_ts = now_ts

    top_n = max(1, int(ctx.top_n))
    top_cpu = sorted(top_cpu_scored, key=lambda t: t[2], reverse=True)[:top_n]
    top_cpu = [(idx + 1, s, v) for idx, (_, s, v) in enumerate(top_cpu)]

    top_rss_samples = sorted(samples, key=lambda s: s.rss_bytes, reverse=True)[:top_n]
    top_rss = [(idx + 1, s) for idx, s in enumerate(top_rss_samples)]

    mem_total_bytes = _read_mem_total_bytes(ctx.proc_root)
    content = render(top_cpu=top_cpu, top_rss=top_rss, mem_total_bytes=mem_total_bytes)
    write_atomically(ctx.output_file, content)


def main() -> int:
    """CLI entrypoint: periodically write top process metrics to a textfile directory."""
    args = _parse_args()

    proc_root = Path(args.proc_root)
    output_dir = Path(args.output_dir)
    output_file = output_dir / "top_processes.prom"

    clk_tck = int(os.sysconf("SC_CLK_TCK"))
    page_size = int(os.sysconf("SC_PAGE_SIZE"))

    ctx = _RunContext(
        proc_root=proc_root,
        output_file=output_file,
        clk_tck=clk_tck,
        page_size=page_size,
        top_n=args.top_n,
    )
    state = _RunState(prev_cpu={}, prev_ts=time.monotonic())

    if args.interval_seconds <= 0:
        _run_once(ctx, state, interval_seconds=0.0)
        return 0

    while True:
        _run_once(ctx, state, interval_seconds=args.interval_seconds)
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
