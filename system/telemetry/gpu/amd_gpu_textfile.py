#!/usr/bin/env python3
"""AMD GPU metrics to Prometheus node_exporter textfile collector.

This script reads AMDGPU stats from sysfs (no ROCm required) and writes a
Prometheus textfile (node_exporter textfile collector format).

Metrics emitted (when available):
- node_textfile_gpu_temperature_celsius{gpu="cardX"}
- node_textfile_gpu_power_watts{gpu="cardX"}
- node_textfile_gpu_clock_frequency_hz{gpu="cardX"}
- node_textfile_gpu_memory_used_bytes{gpu="cardX"}
- node_textfile_gpu_memory_total_bytes{gpu="cardX"}
- node_textfile_gpu_utilization_percent{gpu="cardX"}
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


AMD_VENDOR_HEX = "0x1002"


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_int(path: Path) -> Optional[int]:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _read_float(path: Path) -> Optional[float]:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _find_hwmon_dir(device_dir: Path) -> Optional[Path]:
    hwmon_root = device_dir / "hwmon"
    if not hwmon_root.exists():
        return None
    for child in hwmon_root.iterdir():
        # /sys/class/drm/cardX/device/hwmon/hwmonY
        if child.is_dir() and child.name.startswith("hwmon"):
            return child
    return None


def _parse_pp_dpm_current_khz(path: Path) -> Optional[int]:
    """Parse pp_dpm_sclk/pp_dpm_mclk and return current frequency in kHz."""
    text = _read_text(path)
    if not text:
        return None

    # Typical lines:
    # 0: 300Mhz
    # 1: 800Mhz *
    # Some drivers use "MHz" or "Mhz".
    current_line = None
    for line in text.splitlines():
        if "*" in line:
            current_line = line
            break
    if current_line is None:
        # Fallback: take the last line (often highest state)
        current_line = text.splitlines()[-1]

    m = re.search(r"([0-9]+)\s*[mM][hH][zZ]", current_line)
    if not m:
        return None
    mhz = int(m.group(1))
    return mhz * 1000


@dataclass(frozen=True)
class GpuMetrics:
    gpu: str
    temperature_c: Optional[float]
    power_w: Optional[float]
    clock_hz: Optional[float]
    vram_used_bytes: Optional[float]
    vram_total_bytes: Optional[float]
    utilization_percent: Optional[float]


def _collect_for_card(card_dir: Path) -> Optional[GpuMetrics]:
    # card_dir: /sys/class/drm/cardX
    device_dir = card_dir / "device"
    vendor = _read_text(device_dir / "vendor")
    if vendor != AMD_VENDOR_HEX:
        return None

    gpu_label = card_dir.name  # e.g. "card0"

    # Utilization (if supported)
    utilization_percent = _read_float(device_dir / "gpu_busy_percent")

    # VRAM usage (if supported)
    vram_used = _read_int(device_dir / "mem_info_vram_used")
    vram_total = _read_int(device_dir / "mem_info_vram_total")

    # Clocks (prefer sclk)
    sclk_khz = _parse_pp_dpm_current_khz(device_dir / "pp_dpm_sclk")
    clock_hz = float(sclk_khz * 1000) if sclk_khz is not None else None

    # Temperature + power (hwmon)
    temperature_c = None
    power_w = None
    hwmon_dir = _find_hwmon_dir(device_dir)
    if hwmon_dir is not None:
        # temp1_input: millidegree C
        temp_milli_c = _read_int(hwmon_dir / "temp1_input")
        if temp_milli_c is not None:
            temperature_c = temp_milli_c / 1000.0

        # power1_average: microwatt (some systems expose power1_input instead)
        power_u_w = _read_int(hwmon_dir / "power1_average")
        if power_u_w is None:
            power_u_w = _read_int(hwmon_dir / "power1_input")
        if power_u_w is not None:
            power_w = power_u_w / 1_000_000.0

    return GpuMetrics(
        gpu=gpu_label,
        temperature_c=temperature_c,
        power_w=power_w,
        clock_hz=clock_hz,
        vram_used_bytes=float(vram_used) if vram_used is not None else None,
        vram_total_bytes=float(vram_total) if vram_total is not None else None,
        utilization_percent=utilization_percent,
    )


def collect() -> list[GpuMetrics]:
    drm_dir = Path("/sys/class/drm")
    if not drm_dir.exists():
        return []

    gpus: list[GpuMetrics] = []
    for child in sorted(drm_dir.iterdir()):
        if not child.is_dir():
            continue
        if not re.fullmatch(r"card[0-9]+", child.name):
            continue
        metrics = _collect_for_card(child)
        if metrics is not None:
            gpus.append(metrics)
    return gpus


def render(metrics: list[GpuMetrics]) -> str:
    # NOTE: The node_exporter textfile collector is strict about exposition
    # format. In particular, repeating HELP/TYPE blocks for the same metric name
    # can trigger a scrape error. We therefore emit HELP/TYPE once per metric,
    # then all samples for that metric.

    # Metric metadata: name -> (help, type)
    meta: dict[str, tuple[str, str]] = {
        "node_textfile_gpu_temperature_celsius": (
            "GPU temperature in Celsius (from AMDGPU sysfs/hwmon).",
            "gauge",
        ),
        "node_textfile_gpu_power_watts": (
            "GPU power draw in watts (from AMDGPU sysfs/hwmon).",
            "gauge",
        ),
        "node_textfile_gpu_clock_frequency_hz": (
            "Current GPU core clock frequency in Hz (from pp_dpm_sclk).",
            "gauge",
        ),
        "node_textfile_gpu_memory_used_bytes": (
            "GPU VRAM used in bytes (from mem_info_vram_used).",
            "gauge",
        ),
        "node_textfile_gpu_memory_total_bytes": (
            "GPU VRAM total in bytes (from mem_info_vram_total).",
            "gauge",
        ),
        "node_textfile_gpu_utilization_percent": (
            "GPU utilization percent (from gpu_busy_percent).",
            "gauge",
        ),
    }

    # Metric samples: name -> list of (gpu_label, value)
    samples: dict[str, list[tuple[str, float]]] = {k: [] for k in meta}
    for gpu in metrics:
        if gpu.temperature_c is not None:
            samples["node_textfile_gpu_temperature_celsius"].append((gpu.gpu, gpu.temperature_c))
        if gpu.power_w is not None:
            samples["node_textfile_gpu_power_watts"].append((gpu.gpu, gpu.power_w))
        if gpu.clock_hz is not None:
            samples["node_textfile_gpu_clock_frequency_hz"].append((gpu.gpu, gpu.clock_hz))
        if gpu.vram_used_bytes is not None:
            samples["node_textfile_gpu_memory_used_bytes"].append((gpu.gpu, gpu.vram_used_bytes))
        if gpu.vram_total_bytes is not None:
            samples["node_textfile_gpu_memory_total_bytes"].append((gpu.gpu, gpu.vram_total_bytes))
        if gpu.utilization_percent is not None:
            samples["node_textfile_gpu_utilization_percent"].append((gpu.gpu, gpu.utilization_percent))

    lines: list[str] = []
    any_samples = any(len(v) > 0 for v in samples.values())
    if not any_samples:
        return "# No AMD GPU metrics found (no AMDGPU sysfs entries detected).\n"

    for metric_name, (help_text, metric_type) in meta.items():
        metric_samples = samples[metric_name]
        if not metric_samples:
            continue
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} {metric_type}")
        for gpu_label, value in metric_samples:
            lines.append(f'{metric_name}{{gpu="{gpu_label}"}} {value}')

    return "\n".join(lines) + "\n"


def write_atomically(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, output_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for node_exporter textfile collector (mounted volume).",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=5.0,
        help="Polling interval. Use 0 to run once and exit.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_file = output_dir / "amd_gpu.prom"

    def run_once() -> None:
        content = render(collect())
        write_atomically(output_file, content)

    if args.interval_seconds <= 0:
        run_once()
        return 0

    while True:
        run_once()
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())


