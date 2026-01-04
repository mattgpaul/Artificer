#!/usr/bin/env python3
"""AMD GPU metrics to Prometheus node_exporter textfile collector.

This script reads AMDGPU stats from sysfs (no ROCm required) and writes a
Prometheus textfile (node_exporter textfile collector format).

Metrics emitted (when available):
- node_textfile_gpu_model{gpu="cardX",model="..."}
- node_textfile_gpu_temperature_celsius{gpu="cardX"}
- node_textfile_gpu_power_watts{gpu="cardX"}
- node_textfile_gpu_clock_frequency_hz{gpu="cardX"}
- node_textfile_gpu_clock_max_frequency_hz{gpu="cardX"}
- node_textfile_gpu_memory_used_bytes{gpu="cardX"}
- node_textfile_gpu_memory_total_bytes{gpu="cardX"}
- node_textfile_gpu_utilization_percent{gpu="cardX"}
- node_textfile_gpu_fan_rpm{gpu="cardX"}
- node_textfile_gpu_fan_max_rpm{gpu="cardX"}
"""

from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

AMD_VENDOR_HEX = "0x1002"


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_int(path: Path) -> int | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _read_float(path: Path) -> float | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _find_hwmon_dir(device_dir: Path) -> Path | None:
    hwmon_root = device_dir / "hwmon"
    if not hwmon_root.exists():
        return None
    for child in hwmon_root.iterdir():
        # /sys/class/drm/cardX/device/hwmon/hwmonY
        if child.is_dir() and child.name.startswith("hwmon"):
            return child
    return None


def _parse_pp_dpm_current_khz(path: Path) -> int | None:
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


def _parse_pp_dpm_max_khz(path: Path) -> int | None:
    """Parse pp_dpm_sclk/pp_dpm_mclk and return maximum advertised frequency in kHz."""
    text = _read_text(path)
    if not text:
        return None
    mhz_values: list[int] = []
    for line in text.splitlines():
        m = re.search(r"([0-9]+)\s*[mM][hH][zZ]", line)
        if m:
            mhz_values.append(int(m.group(1)))
    if not mhz_values:
        return None
    return max(mhz_values) * 1000


@dataclass(frozen=True)
class GpuMetrics:
    """Snapshot of AMDGPU metrics for a single DRM card."""

    gpu: str
    model: str | None
    temperature_c: float | None
    power_w: float | None
    clock_hz: float | None
    clock_max_hz: float | None
    vram_used_bytes: float | None
    vram_total_bytes: float | None
    utilization_percent: float | None
    fan_rpm: float | None
    fan_max_rpm: float | None


def _escape_label_value(value: str) -> str:
    """Escape a Prometheus label value for text exposition format."""
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _format_sample_line(metric_name: str, labels: dict[str, str], value: float) -> str:
    label_items = [f'{k}="{_escape_label_value(v)}"' for k, v in labels.items()]
    return f"{metric_name}{{{','.join(label_items)}}} {value:g}"


@dataclass(frozen=True)
class _MetricDef:
    name: str
    help: str
    type: str
    attr: str


_METRICS: tuple[_MetricDef, ...] = (
    _MetricDef(
        name="node_textfile_gpu_model",
        help="GPU model name (from sysfs device/product_name or TELEMETRY_GPU_NAME override).",
        type="gauge",
        attr="model",
    ),
    _MetricDef(
        name="node_textfile_gpu_temperature_celsius",
        help="GPU temperature in Celsius (from AMDGPU sysfs/hwmon).",
        type="gauge",
        attr="temperature_c",
    ),
    _MetricDef(
        name="node_textfile_gpu_power_watts",
        help="GPU power draw in watts (from AMDGPU sysfs/hwmon).",
        type="gauge",
        attr="power_w",
    ),
    _MetricDef(
        name="node_textfile_gpu_clock_frequency_hz",
        help="Current GPU core clock frequency in Hz (from pp_dpm_sclk).",
        type="gauge",
        attr="clock_hz",
    ),
    _MetricDef(
        name="node_textfile_gpu_clock_max_frequency_hz",
        help="Maximum advertised GPU core clock frequency in Hz (from pp_dpm_sclk).",
        type="gauge",
        attr="clock_max_hz",
    ),
    _MetricDef(
        name="node_textfile_gpu_memory_used_bytes",
        help="GPU VRAM used in bytes (from mem_info_vram_used).",
        type="gauge",
        attr="vram_used_bytes",
    ),
    _MetricDef(
        name="node_textfile_gpu_memory_total_bytes",
        help="GPU VRAM total in bytes (from mem_info_vram_total).",
        type="gauge",
        attr="vram_total_bytes",
    ),
    _MetricDef(
        name="node_textfile_gpu_utilization_percent",
        help="GPU utilization percent (from gpu_busy_percent).",
        type="gauge",
        attr="utilization_percent",
    ),
    _MetricDef(
        name="node_textfile_gpu_fan_rpm",
        help="GPU fan speed in RPM (from hwmon fan1_input, if present).",
        type="gauge",
        attr="fan_rpm",
    ),
    _MetricDef(
        name="node_textfile_gpu_fan_max_rpm",
        help="GPU fan max speed in RPM (from hwmon fan1_max, if present).",
        type="gauge",
        attr="fan_max_rpm",
    ),
)


def _iter_metric_samples(
    defn: _MetricDef, gpus: list[GpuMetrics]
) -> list[tuple[dict[str, str], float]]:
    samples: list[tuple[dict[str, str], float]] = []
    if defn.attr == "model":
        for gpu in gpus:
            if gpu.model:
                samples.append(({"gpu": gpu.gpu, "model": gpu.model}, 1.0))
        return samples

    for gpu in gpus:
        value = getattr(gpu, defn.attr)
        if value is None:
            continue
        samples.append(({"gpu": gpu.gpu}, float(value)))
    return samples


def _collect_for_card(card_dir: Path) -> GpuMetrics | None:
    # card_dir: /sys/class/drm/cardX
    device_dir = card_dir / "device"
    vendor = _read_text(device_dir / "vendor")
    if vendor != AMD_VENDOR_HEX:
        return None

    gpu_label = card_dir.name  # e.g. "card0"
    # Best-effort model string:
    # - optional override via env TELEMETRY_GPU_NAME
    # - try sysfs product_name
    # - fallback to PCI IDs (still more informative than "AMD GPU")
    override = os.environ.get("TELEMETRY_GPU_NAME", "").strip()
    product_name = _read_text(device_dir / "product_name")
    if override:
        model = override
    elif product_name:
        model = product_name
    else:
        vendor_id = _read_text(device_dir / "vendor") or "unknown"
        device_id = _read_text(device_dir / "device") or "unknown"
        model = f"AMD GPU ({vendor_id}:{device_id})"

    # Utilization (if supported)
    utilization_percent = _read_float(device_dir / "gpu_busy_percent")

    # VRAM usage (if supported)
    vram_used = _read_int(device_dir / "mem_info_vram_used")
    vram_total = _read_int(device_dir / "mem_info_vram_total")

    # Clocks (prefer sclk)
    sclk_khz = _parse_pp_dpm_current_khz(device_dir / "pp_dpm_sclk")
    clock_hz = float(sclk_khz * 1000) if sclk_khz is not None else None
    sclk_max_khz = _parse_pp_dpm_max_khz(device_dir / "pp_dpm_sclk")
    clock_max_hz = float(sclk_max_khz * 1000) if sclk_max_khz is not None else None

    # Temperature + power (hwmon)
    temperature_c = None
    power_w = None
    fan_rpm = None
    fan_max_rpm = None
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

        # Fan RPM (best-effort; some cards expose fan1_input/fan1_max)
        fan_input = _read_int(hwmon_dir / "fan1_input")
        if fan_input is not None:
            fan_rpm = float(fan_input)
        fan_max = _read_int(hwmon_dir / "fan1_max")
        if fan_max is not None:
            fan_max_rpm = float(fan_max)

    return GpuMetrics(
        gpu=gpu_label,
        model=model,
        temperature_c=temperature_c,
        power_w=power_w,
        clock_hz=clock_hz,
        clock_max_hz=clock_max_hz,
        vram_used_bytes=float(vram_used) if vram_used is not None else None,
        vram_total_bytes=float(vram_total) if vram_total is not None else None,
        utilization_percent=utilization_percent,
        fan_rpm=fan_rpm,
        fan_max_rpm=fan_max_rpm,
    )


def collect() -> list[GpuMetrics]:
    """Collect AMDGPU metrics from sysfs for all detected DRM cards."""
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
    """Render Prometheus textfile collector output for provided GPU metrics."""
    # NOTE: The node_exporter textfile collector is strict about exposition
    # format. In particular, repeating HELP/TYPE blocks for the same metric name
    # can trigger a scrape error. We therefore emit HELP/TYPE once per metric,
    # then all samples for that metric.
    lines: list[str] = []
    any_emitted = False
    for defn in _METRICS:
        metric_samples = _iter_metric_samples(defn, metrics)
        if not metric_samples:
            continue
        any_emitted = True
        lines.append(f"# HELP {defn.name} {defn.help}")
        lines.append(f"# TYPE {defn.name} {defn.type}")
        for labels, value in metric_samples:
            lines.append(_format_sample_line(defn.name, labels, value))

    if not any_emitted:
        return "# No AMD GPU metrics found (no AMDGPU sysfs entries detected).\n"

    return "\n".join(lines) + "\n"


def write_atomically(output_path: Path, content: str) -> None:
    """Write the textfile content to disk atomically (write temp, then replace)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, output_path)


def main() -> int:
    """CLI entrypoint: continuously write AMD GPU metrics to a textfile directory."""
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
