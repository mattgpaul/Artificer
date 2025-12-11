#!/bin/bash
# Drop into InfluxDB container with bash shell

set -e

# Exec into container with bash shell
exec docker exec -it influxdb /bin/bash

