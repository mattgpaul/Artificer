#!/bin/bash
# Drop into Grafana container with bash shell

set -e

# Exec into container with bash shell
exec docker exec -it algo_trader-grafana /bin/bash

