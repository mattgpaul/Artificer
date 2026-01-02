# Telemetry Monitoring Stack

A robust Prometheus + Grafana telemetry monitoring system built with Bazel and Docker Compose, designed to replace Conky with a scalable, network-aware solution.

## Architecture

The stack supports two deployment modes:

- **Central Mode**: A central Linux box (e.g., Raspberry Pi) runs Prometheus + Grafana. Each Linux host runs node_exporter and is scraped by the central Prometheus.
- **Local Display Mode**: Any host can run Grafana (or the full stack) and point to the central Prometheus for displaying dashboards.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Bazel installed
- Images built via Bazel (see below)

Note: On some systems, Compose is available as `docker-compose` (standalone).
On others, it is available as `docker compose` (Docker CLI plugin). This repo’s
examples use `docker-compose` because it works even when the plugin subcommand
is not installed.

### Building Images

Build all required images:

```bash
# Build Prometheus image
bazel run //infrastructure/prometheus:prometheus_image

# Build node_exporter image
bazel run //infrastructure/node_exporter:node_exporter_image

# Build Grafana image (if not already built)
bazel run //infrastructure/grafana:grafana_image
```

### Central Box Deployment

On your central monitoring box (e.g., Raspberry Pi):

1. Navigate to the telemetry ops directory:
```bash
cd system/telemetry/ops
```

2. Start the central stack (Prometheus + Grafana):
```bash
docker-compose --profile central up -d
```

If you prefer not to use Compose profiles, you can start the same services by name:

```bash
docker-compose up -d prometheus grafana
```

3. Access Grafana at `http://localhost:3001` (default credentials: admin/admin)

4. Access Prometheus at `http://localhost:9090`

### Node Deployment

On each Linux host you want to monitor:

1. Navigate to the telemetry ops directory:
```bash
cd system/telemetry/ops
```

2. Start node_exporter (this profile only runs the exporter; it will NOT start Grafana):
```bash
docker-compose --profile node up -d
```

If you prefer not to use Compose profiles, you can start the same service by name:

```bash
docker-compose up -d node-exporter
```

3. Add the node to Prometheus file service discovery:
   - Edit `system/telemetry/prometheus/targets/node-exporters.yaml`
   - Add an entry with the node's IP address and port (default 9100)
   - Prometheus will automatically discover it within 30 seconds

### Systemd Service (Optional)

To ensure the stack starts on boot and restarts on failure, create a systemd service:

Create `/etc/systemd/system/telemetry-monitoring.service`:

```ini
[Unit]
Description=Telemetry Monitoring Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/Artificer/system/telemetry/ops
ExecStart=/usr/bin/docker-compose --profile central up -d
ExecStop=/usr/bin/docker-compose --profile central down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telemetry-monitoring.service
sudo systemctl start telemetry-monitoring.service
```

## Configuration

### Prometheus Targets

Edit `system/telemetry/prometheus/targets/node-exporters.yaml` to add/remove nodes. See `system/telemetry/prometheus/targets/README.md` for details.

### Grafana Dashboards

Dashboards are automatically provisioned from `system/telemetry/grafana/provisioning/dashboards/`. You can:
- Edit existing dashboards in Grafana UI (changes persist)
- Add new dashboard JSON files to the directory
- Dashboards auto-refresh every 10 seconds

This stack starts with a single dashboard:
- **Telemetry Overview** (`uid=telemetry-overview`): CPU, memory, disk, network, and optional GPU (textfile collector).

### AMD GPU Metrics

The AMD GPU dashboard expects metrics from node_exporter's textfile collector. To enable:

1. Create a script that exports AMD GPU metrics in Prometheus format
2. Write metrics to `/var/lib/node_exporter/textfile_collector/` (mounted volume)
3. Metrics should follow naming convention: `node_textfile_gpu_*`

Example script using `rocm-smi`:

```bash
#!/bin/bash
OUTPUT_DIR="/var/lib/node_exporter/textfile_collector"
rocm-smi --showtemp --showuse --showmemuse --showpower --showclocks --json > /tmp/gpu.json
# Parse and write Prometheus format metrics to $OUTPUT_DIR/gpu.prom
```

## Robustness Features

- **Offline Node Handling**: Prometheus keeps historical data. When nodes go offline, `up=0` and dashboards show "Last Seen" timestamps
- **File-based Service Discovery**: Add/remove nodes without restarting Prometheus
- **Auto-restart**: Docker Compose `restart: unless-stopped` ensures services recover from failures
- **Data Retention**: Prometheus retains 30 days of metrics by default (configurable)

## Ports

- **Prometheus**: 9090 (localhost only)
- **Grafana**: 3001 (localhost only) - Note: Different from algo_trader Grafana on 3000
- **node_exporter**: 9100 (localhost only)

## Troubleshooting

### Check service status:
```bash
docker compose --profile central ps
docker compose --profile node ps
```

### View logs:
```bash
docker compose --profile central logs -f
docker compose --profile node logs -f node-exporter
```

### Verify Prometheus is scraping:
Visit `http://localhost:9090/targets` to see scrape target status

### Verify metrics are available:
Visit `http://localhost:9090/graph` and query `up{job="node-exporter"}`

## Scaling

To add more nodes:
1. Deploy node_exporter on the new host (use `node` profile)
2. Add the target to `prometheus/targets/node-exporters.yaml`
3. Prometheus will discover it automatically

To monitor from multiple locations:
- Run Grafana on any machine
- Point it to the central Prometheus URL (ensure firewall allows access)
- Or run full stack locally with `--profile central`

