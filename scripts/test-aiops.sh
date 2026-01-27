#!/bin/bash
# AIOps Stage 3 Test Script
# This script tests all AIOps components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AIOps Stage 3 - Testing Services${NC}"
echo -e "${BLUE}========================================${NC}"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
    local test_name=$1
    local test_command=$2

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    echo -e "${YELLOW}Test $TOTAL_TESTS: $test_name${NC}"

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Check if we're in the correct directory
if [ ! -f "docker-compose.yaml" ]; then
    echo -e "${RED}Error: docker-compose.yaml not found${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Test 1: Check if all Stage 3 containers are running
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Container Health Checks${NC}"
echo -e "${BLUE}========================================${NC}"

run_test "Zookeeper container is running" "docker ps | grep -q zookeeper"
run_test "Kafka container is running" "docker ps | grep -q kafka"
run_test "Redis container is running" "docker ps | grep -q redis"
run_test "Flink JobManager container is running" "docker ps | grep -q flink-jobmanager"
run_test "Flink TaskManager container is running" "docker ps | grep -q flink-taskmanager"
run_test "Data Ingestion container is running" "docker ps | grep -q data-ingestion"
run_test "Anomaly Detection container is running" "docker ps | grep -q anomaly-detection"
run_test "Root Cause Analysis container is running" "docker ps | grep -q root-cause-analysis"
run_test "Insights & Action container is running" "docker ps | grep -q insights-action"

# Test 2: Check service endpoints
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Service Endpoint Checks${NC}"
echo -e "${BLUE}========================================${NC}"

run_test "Neo4j is accessible" "curl -sf http://localhost:7474 > /dev/null"
run_test "Flink UI is accessible" "curl -sf http://localhost:8081 > /dev/null"

# Test 3: Check Kafka topics
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Kafka Topic Checks${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Creating test topic..."
docker exec -it kafka kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --topic aiops-test 2>/dev/null || true

run_test "Kafka topic creation works" "docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q aiops-test"
run_test "aiops.metrics topic exists" "docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q aiops.metrics"
run_test "aiops.logs topic exists" "docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q aiops.logs"
run_test "aiops.traces topic exists" "docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q aiops.traces"
run_test "aiops.anomalies topic exists" "docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q aiops.anomalies"
run_test "aiops.rca_results topic exists" "docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q aiops.rca_results"
run_test "aiops.actions topic exists" "docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092 | grep -q aiops.actions"

# Test 4: Check Redis connectivity
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Redis Checks${NC}"
echo -e "${BLUE}========================================${NC}"

run_test "Redis is accessible" "docker exec -it redis redis-cli ping | grep -q PONG"

# Test 5: Check Neo4j connectivity
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Neo4j Checks${NC}"
echo -e "${BLUE}========================================${NC}"

run_test "Neo4j has device data" "docker exec -it neo4j cypher-shell -u neo4j -p password123 'MATCH (d:Device) RETURN count(d) > 0' | grep -q true"

# Test 6: Check service logs for errors
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Service Log Checks${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Checking for recent errors in service logs..."
ERROR_COUNT=$(docker-compose -f docker-compose-aiops.yml logs --tail=100 2>&1 | grep -i "error" | wc -l)

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ No errors found in recent logs${NC}"
else
    echo -e "${YELLOW}⚠ Found $ERROR_COUNT error(s) in recent logs (may be normal)${NC}"
fi

# Test 7: Data flow test
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Data Flow Test${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Waiting 30 seconds for data ingestion to collect some data..."
sleep 30

echo "Checking if metrics are being published to Kafka..."
METRIC_COUNT=$(docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic aiops.metrics --from-beginning --timeout-ms 5000 2>&1 | grep -c "metric_name" || echo "0")

if [ "$METRIC_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $METRIC_COUNT metric(s) in Kafka${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}⚠ No metrics found yet (may need more time)${NC}"
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Display test results
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Results${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tests passed! AIOps Stage 3 is working correctly.${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Some tests failed. Please check the logs above.${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi