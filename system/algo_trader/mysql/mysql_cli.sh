#!/bin/bash
# Drop into MySQL container with credentials from environment variables

set -e

# Use environment variables (already set from .env or shell)
# Bazel run passes through environment variables from your shell
exec docker exec -it algo_trader-mysql mysql \
    -u "${MYSQL_USER:-algo_trader}" \
    -p"${MYSQL_PASSWORD}" \
    "${MYSQL_DATABASE:-algo_trader}"

