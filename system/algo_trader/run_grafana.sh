#!/bin/bash

# Grafana container management script for Phase 4
# This script handles starting/stopping Grafana container with proper configuration

set -e

CONTAINER_NAME="algo-trader-grafana"
GRAFANA_PORT="3000"
ADMIN_USER="admin"
ADMIN_PASSWORD="admin"

# Function to check if container is running
is_container_running() {
    docker ps --filter "name=${CONTAINER_NAME}" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to check if container exists
container_exists() {
    docker ps -a --filter "name=${CONTAINER_NAME}" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to start Grafana container
start_grafana() {
    echo "Starting Grafana container..."
    
    if is_container_running; then
        echo "Grafana container is already running"
        return 0
    fi
    
    if container_exists; then
        echo "Starting existing Grafana container..."
        docker start "${CONTAINER_NAME}"
    else
        echo "Creating new Grafana container..."
        docker run -d \
            --name "${CONTAINER_NAME}" \
            -p "${GRAFANA_PORT}:3000" \
            -e "GF_SECURITY_ADMIN_USER=${ADMIN_USER}" \
            -e "GF_SECURITY_ADMIN_PASSWORD=${ADMIN_PASSWORD}" \
            grafana/grafana:latest
    fi
    
    # Wait for Grafana to be ready
    echo "Waiting for Grafana to be ready..."
    for i in {1..30}; do
        if curl -s "http://localhost:${GRAFANA_PORT}/api/health" > /dev/null 2>&1; then
            echo "Grafana is ready!"
            echo ""
            echo "Access Grafana at: http://localhost:${GRAFANA_PORT}"
            echo "Admin credentials: ${ADMIN_USER} / ${ADMIN_PASSWORD}"
            echo "Market data dashboard: http://localhost:${GRAFANA_PORT}/d/market-data-candles/market-data-candlestick-charts"
            return 0
        fi
        sleep 2
    done
    
    echo "Warning: Grafana may not be fully ready yet. Check http://localhost:${GRAFANA_PORT}"
    return 1
}

# Function to stop Grafana container
stop_grafana() {
    echo "Stopping Grafana container..."
    if is_container_running; then
        docker stop "${CONTAINER_NAME}"
        echo "Grafana container stopped"
    else
        echo "Grafana container is not running"
    fi
}

# Function to remove Grafana container
remove_grafana() {
    echo "Removing Grafana container..."
    stop_grafana
    if container_exists; then
        docker rm "${CONTAINER_NAME}"
        echo "Grafana container removed"
    else
        echo "Grafana container does not exist"
    fi
}

# Function to show container status
show_status() {
    if is_container_running; then
        echo "Grafana container is running"
        echo "Access at: http://localhost:${GRAFANA_PORT}"
    elif container_exists; then
        echo "Grafana container exists but is not running"
    else
        echo "Grafana container does not exist"
    fi
}

# Main script logic
case "${1:-start}" in
    "start")
        start_grafana
        ;;
    "stop")
        stop_grafana
        ;;
    "restart")
        stop_grafana
        sleep 2
        start_grafana
        ;;
    "remove")
        remove_grafana
        ;;
    "status")
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|remove|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start Grafana container (default)"
        echo "  stop    - Stop Grafana container"
        echo "  restart - Restart Grafana container"
        echo "  remove  - Remove Grafana container"
        echo "  status  - Show container status"
        exit 1
        ;;
esac


