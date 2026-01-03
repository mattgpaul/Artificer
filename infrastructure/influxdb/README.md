# InfluxDB Server Binary

## Usage

Start InfluxDB server for development:

```bash
# Default configuration (port 8086, admin UI on 8083)
bazel run //infrastructure/influxdb:influxdb_server

# Custom port
bazel run //infrastructure/influxdb:influxdb_server -- --port 8087

# Custom data directory
bazel run //infrastructure/influxdb:influxdb_server -- --data-dir /tmp/influxdb-dev

# Custom configuration file
bazel run //infrastructure/influxdb:influxdb_server -- --config /path/to/influxdb.yml
```

## Default Configuration

- **HTTP API**: http://localhost:8086
- **Admin UI**: http://localhost:8083
- **Admin User**: admin
- **Admin Password**: admin123
- **Default Database**: market_data
- **Data Directory**: ./influxdb-data

## Requirements

- Docker must be installed and running
- Ports 8086 and 8083 must be available

## Environment Variables

The server will automatically set up these environment variables for your services:
- `INFLUXDB_HOST=localhost`
- `INFLUXDB_PORT=8086`
- `INFLUXDB_DATABASE=market_data`
- `INFLUXDB3_AUTH_TOKEN` (generated automatically)

## Stopping the Server

Press Ctrl+C to stop the server gracefully.

