# Prometheus File Service Discovery Targets

This directory contains target files for Prometheus file-based service discovery.

## Adding a New Node

To add a new Linux host to be monitored:

1. Create a new YAML file (or edit `node-exporters.yaml`) with the target configuration:

```yaml
- targets:
    - '192.168.1.100:9100'  # Replace with your node's IP and node_exporter port
  labels:
    instance: 'my-desktop'
    host: 'my-desktop.local'
    site: 'home'
    role: 'workstation'
```

2. Ensure the node_exporter is running on that host (use the `node` profile in docker-compose.yaml)

3. Prometheus will automatically discover the new target within 30 seconds (refresh_interval)

## File Format

Each target file should be a YAML list of target groups:

```yaml
- targets:
    - 'host1:9100'
    - 'host2:9100'
  labels:
    instance: 'host1'
    host: 'host1.local'
    site: 'datacenter'
    role: 'server'
```

## Labels

Common labels you can use:
- `instance`: Unique identifier for this target
- `host`: Hostname or FQDN
- `site`: Location identifier (e.g., 'home', 'office', 'datacenter')
- `role`: Machine role (e.g., 'workstation', 'server', 'raspberry-pi')

These labels will be available in Prometheus queries and Grafana dashboards for filtering and grouping.

