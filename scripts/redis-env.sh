#!/bin/bash
# Redis Environment Management
# Industry standard: Different Redis setups for different environments

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo "🔧 Redis Environment Management"
    echo ""
    echo "Usage: $0 <environment> <action>"
    echo ""
    echo "Environments:"
    echo "  dev        - Development (simple Redis)"
    echo "  prod       - Production (clustered Redis)"
    echo "  existing   - Use existing Redis container"
    echo ""
    echo "Actions:"
    echo "  start      - Start Redis for environment"
    echo "  stop       - Stop Redis for environment" 
    echo "  status     - Show Redis status"
    echo "  test       - Test Redis connectivity"
    echo "  logs       - Show Redis logs"
    echo ""
    echo "Examples:"
    echo "  $0 dev start       - Start development Redis"
    echo "  $0 existing test   - Test existing Redis"
    echo "  $0 prod status     - Check production Redis cluster"
}

start_redis() {
    local env=$1
    
    case $env in
        dev)
            echo -e "${BLUE}🚀 Starting Development Redis...${NC}"
            cd infrastructure/redis/development
            docker-compose up -d
            echo -e "${GREEN}✅ Development Redis started${NC}"
            echo "   Redis: localhost:6379"
            echo "   UI: http://localhost:8081"
            ;;
        prod)
            echo -e "${BLUE}🚀 Starting Production Redis Cluster...${NC}"
            echo -e "${YELLOW}⚠️  Production setup is complex. Consider managed Redis (AWS ElastiCache, etc.)${NC}"
            cd infrastructure/redis/production  
            docker-compose -f redis-cluster.yml up -d
            echo -e "${GREEN}✅ Production Redis cluster started${NC}"
            echo "   Nodes: localhost:7000, localhost:7001, localhost:7002"
            ;;
        existing)
            echo -e "${YELLOW}ℹ️  Using existing Redis container${NC}"
            if docker ps | grep -q redis; then
                echo -e "${GREEN}✅ Existing Redis found and running${NC}"
            else
                echo -e "${RED}❌ No existing Redis container found${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}❌ Unknown environment: $env${NC}"
            show_help
            exit 1
            ;;
    esac
}

stop_redis() {
    local env=$1
    
    case $env in
        dev)
            echo -e "${BLUE}🛑 Stopping Development Redis...${NC}"
            cd infrastructure/redis/development
            docker-compose down
            echo -e "${GREEN}✅ Development Redis stopped${NC}"
            ;;
        prod)
            echo -e "${BLUE}🛑 Stopping Production Redis...${NC}"
            cd infrastructure/redis/production
            docker-compose -f redis-cluster.yml down
            echo -e "${GREEN}✅ Production Redis stopped${NC}"
            ;;
        existing)
            echo -e "${YELLOW}⚠️  Not stopping existing Redis (managed externally)${NC}"
            ;;
        *)
            echo -e "${RED}❌ Unknown environment: $env${NC}"
            exit 1
            ;;
    esac
}

test_redis() {
    local env=$1
    
    echo -e "${BLUE}🧪 Testing Redis connectivity...${NC}"
    
    case $env in
        dev)
            if docker exec artificer-redis-dev redis-cli ping > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Development Redis is responding${NC}"
                # Test queue operations
                docker exec artificer-redis-dev redis-cli lpush test:queue "test message" > /dev/null
                local length=$(docker exec artificer-redis-dev redis-cli llen test:queue)
                docker exec artificer-redis-dev redis-cli del test:queue > /dev/null
                
                if [[ "$length" == "1" ]]; then
                    echo -e "${GREEN}✅ Queue operations working${NC}"
                else
                    echo -e "${RED}❌ Queue operations failed${NC}"
                fi
            else
                echo -e "${RED}❌ Development Redis not responding${NC}"
                echo "Try: $0 dev start"
            fi
            ;;
        existing)
            # Find existing Redis container
            local redis_container=$(docker ps --format "{{.Names}}" | grep redis | head -1)
            
            if [[ -n "$redis_container" ]]; then
                if docker exec "$redis_container" redis-cli ping > /dev/null 2>&1; then
                    echo -e "${GREEN}✅ Existing Redis ($redis_container) is responding${NC}"
                    
                    # Test telemetry queue operations
                    docker exec "$redis_container" redis-cli lpush telemetry:test "test message" > /dev/null
                    local length=$(docker exec "$redis_container" redis-cli llen telemetry:test)
                    docker exec "$redis_container" redis-cli del telemetry:test > /dev/null
                    
                    if [[ "$length" == "1" ]]; then
                        echo -e "${GREEN}✅ Telemetry queue operations working${NC}"
                    else
                        echo -e "${RED}❌ Telemetry queue operations failed${NC}"
                    fi
                else
                    echo -e "${RED}❌ Existing Redis not responding${NC}"
                fi
            else
                echo -e "${RED}❌ No Redis container found${NC}"
            fi
            ;;
        prod)
            echo -e "${YELLOW}⚠️  Production Redis testing requires cluster client${NC}"
            echo "Use redis-cli --cluster check localhost:7000 for cluster status"
            ;;
    esac
}

show_status() {
    local env=$1
    
    echo -e "${BLUE}📊 Redis Status ($env environment)${NC}"
    echo ""
    
    case $env in
        dev)
            if docker ps | grep artificer-redis-dev > /dev/null; then
                echo -e "${GREEN}✅ Development Redis running${NC}"
                echo "📈 Memory usage:"
                docker exec artificer-redis-dev redis-cli info memory | grep used_memory_human
            else
                echo -e "${RED}❌ Development Redis not running${NC}"
            fi
            ;;
        existing)
            local redis_containers=$(docker ps --format "{{.Names}}" | grep redis)
            if [[ -n "$redis_containers" ]]; then
                echo -e "${GREEN}✅ Existing Redis containers:${NC}"
                echo "$redis_containers"
            else
                echo -e "${RED}❌ No Redis containers running${NC}"
            fi
            ;;
        prod)
            echo -e "${BLUE}📊 Production Redis Cluster Status:${NC}"
            local cluster_nodes=$(docker ps --format "{{.Names}}" | grep redis-cluster-node)
            if [[ -n "$cluster_nodes" ]]; then
                echo -e "${GREEN}✅ Cluster nodes running:${NC}"
                echo "$cluster_nodes"
            else
                echo -e "${RED}❌ No cluster nodes running${NC}"
            fi
            ;;
    esac
}

# Main command handling
ENV=${1:-}
ACTION=${2:-}

if [[ -z "$ENV" || -z "$ACTION" ]]; then
    show_help
    exit 1
fi

case $ACTION in
    start)
        start_redis "$ENV"
        ;;
    stop)
        stop_redis "$ENV"
        ;;
    status)
        show_status "$ENV"
        ;;
    test)
        test_redis "$ENV"
        ;;
    logs)
        echo "Logs for $ENV environment..."
        # Add log commands based on environment
        ;;
    *)
        echo -e "${RED}❌ Unknown action: $ACTION${NC}"
        show_help
        exit 1
        ;;
esac
