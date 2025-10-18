#!/bin/bash

# Grafana container management script using docker-compose
# This script provides a convenient wrapper around docker-compose for Grafana

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if docker-compose is available
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}Error: docker-compose is not installed${NC}"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# Function to start Grafana
start_grafana() {
    echo -e "${GREEN}Starting Grafana container...${NC}"
    cd "$PROJECT_ROOT"
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d grafana
    
    echo -e "${YELLOW}Waiting for Grafana to be ready...${NC}"
    for i in {1..30}; do
        if curl -s "http://localhost:3000/api/health" > /dev/null 2>&1; then
            echo -e "${GREEN}Grafana is ready!${NC}"
            echo ""
            echo "Access Grafana at: http://localhost:3000"
            echo "Authentication: DISABLED (no login required)"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${YELLOW}Warning: Grafana may not be fully ready yet. Check http://localhost:3000${NC}"
    return 1
}

# Function to stop Grafana
stop_grafana() {
    echo -e "${YELLOW}Stopping Grafana container...${NC}"
    cd "$PROJECT_ROOT"
    $COMPOSE_CMD -f "$COMPOSE_FILE" stop grafana
    echo -e "${GREEN}Grafana container stopped${NC}"
}

# Function to restart Grafana
restart_grafana() {
    echo -e "${YELLOW}Restarting Grafana container...${NC}"
    stop_grafana
    sleep 2
    start_grafana
}

# Function to show Grafana status
show_status() {
    cd "$PROJECT_ROOT"
    $COMPOSE_CMD -f "$COMPOSE_FILE" ps grafana
}

# Function to show Grafana logs
show_logs() {
    cd "$PROJECT_ROOT"
    $COMPOSE_CMD -f "$COMPOSE_FILE" logs -f grafana
}

# Function to remove Grafana container and volumes
remove_grafana() {
    echo -e "${RED}Removing Grafana container and volumes...${NC}"
    cd "$PROJECT_ROOT"
    $COMPOSE_CMD -f "$COMPOSE_FILE" down -v
    echo -e "${GREEN}Grafana container and volumes removed${NC}"
}

# Main script logic
check_docker_compose

case "${1:-start}" in
    "start")
        start_grafana
        ;;
    "stop")
        stop_grafana
        ;;
    "restart")
        restart_grafana
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "remove")
        remove_grafana
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|remove}"
        echo ""
        echo "Commands:"
        echo "  start   - Start Grafana container (default)"
        echo "  stop    - Stop Grafana container"
        echo "  restart - Restart Grafana container"
        echo "  status  - Show Grafana container status"
        echo "  logs    - Show Grafana logs (follow mode)"
        echo "  remove  - Remove Grafana container and volumes"
        exit 1
        ;;
esac

