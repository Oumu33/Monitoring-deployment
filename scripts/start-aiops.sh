#!/bin/bash
# AIOps Stage 3 Startup Script
# This script starts all AIOps components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AIOps Stage 3 - Starting Services${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

# Check if we're in the correct directory
if [ ! -f "docker-compose.yaml" ]; then
    echo -e "${RED}Error: docker-compose.yaml not found${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local health_check_url=$2
    local max_attempts=30
    local attempt=0

    echo -e "${YELLOW}Waiting for $service_name to be ready...${NC}"

    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$health_check_url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $service_name is ready${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done

    echo -e "${RED}✗ $service_name failed to start${NC}"
    return 1
}

# Step 1: Check if Stage 1 and Stage 2 are running
echo ""
echo -e "${YELLOW}Step 1: Checking if Stage 1 and Stage 2 services are running...${NC}"

if ! docker ps | grep -q "victoriametrics"; then
    echo -e "${RED}Error: VictoriaMetrics is not running. Please start Stage 1 first.${NC}"
    exit 1
fi

if ! docker ps | grep -q "loki"; then
    echo -e "${RED}Error: Loki is not running. Please start Stage 1 first.${NC}"
    exit 1
fi

if ! docker ps | grep -q "tempo"; then
    echo -e "${RED}Error: Tempo is not running. Please start Stage 2 first.${NC}"
    exit 1
fi

if ! docker ps | grep -q "neo4j"; then
    echo -e "${RED}Error: Neo4j is not running. Please start Stage 2 first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisite services are running${NC}"

# Step 2: Build and start Stage 3 services
echo ""
echo -e "${YELLOW}Step 2: Building and starting AIOps Stage 3 services...${NC}"

# Build the images
docker-compose -f docker-compose-aiops.yml build

# Start the services
docker-compose -f docker-compose-aiops.yml up -d

echo -e "${GREEN}✓ AIOps Stage 3 services started${NC}"

# Step 3: Wait for critical services to be ready
echo ""
echo -e "${YELLOW}Step 3: Waiting for services to be healthy...${NC}"

# Wait for Zookeeper
wait_for_service "Zookeeper" "http://localhost:2181" || true

# Wait for Kafka
wait_for_service "Kafka" "http://localhost:9092" || true

# Wait for Redis
wait_for_service "Redis" "http://localhost:6379" || true

# Wait for Neo4j
wait_for_service "Neo4j" "http://localhost:7474" || true

# Wait for Flink
wait_for_service "Flink JobManager" "http://localhost:8081" || true

# Step 4: Display service status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AIOps Stage 3 - Service Status${NC}"
echo -e "${GREEN}========================================${NC}"

docker-compose -f docker-compose-aiops.yml ps

# Step 5: Display access information
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AIOps Stage 3 - Access Information${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service URLs:"
echo "  - Zookeeper:     http://localhost:2181"
echo "  - Kafka:         http://localhost:9092"
echo "  - Redis:         http://localhost:6379"
echo "  - Flink UI:      http://localhost:8081"
echo "  - Neo4j Browser: http://localhost:7474 (neo4j/password123)"
echo ""
echo "Service Logs:"
echo "  - Data Ingestion:    docker-compose -f docker-compose-aiops.yml logs -f data-ingestion"
echo "  - Anomaly Detection: docker-compose -f docker-compose-aiops.yml logs -f anomaly-detection"
echo "  - Root Cause Analysis: docker-compose -f docker-compose-aiops.yml logs -f root-cause-analysis"
echo "  - Insights & Action: docker-compose -f docker-compose-aiops.yml logs -f insights-action"
echo ""
echo "Kafka Topics (for debugging):"
echo "  - List topics:    docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092"
echo "  - Consume metrics: docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.metrics --from-beginning"
echo "  - Consume anomalies: docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.anomalies --from-beginning"
echo "  - Consume RCA results: docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.rca_results --from-beginning"
echo ""
echo "Redis CLI:"
echo "  - docker exec -it redis redis-cli"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AIOps Stage 3 - Successfully Started!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Monitor service logs to ensure all components are working"
echo "  2. Check Grafana for AIOps annotations"
echo "  3. Review Alertmanager for enriched alerts"
echo "  4. Run test scripts to verify functionality"
echo ""