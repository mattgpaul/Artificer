#!/bin/bash
# Drop into MySQL daemon container with bash shell

set -e

# Exec into container with bash shell
exec docker exec -it algo_trader-mysql-daemon /bin/bash

