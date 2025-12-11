#!/bin/bash
# Drop into InfluxDB publisher container with bash shell

set -e

# Exec into container with bash shell
exec docker exec -it algo_trader-influx-publisher /bin/bash

