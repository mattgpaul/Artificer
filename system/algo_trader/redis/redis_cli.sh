#!/bin/bash
# Drop into Redis container with redis-cli

set -e

# Exec into container with redis-cli
exec docker exec -it algo_trader-redis redis-cli

