#!/bin/bash
# AIOps Stage 3 Stop Script
# This script stops all AIOps Stage 3 components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}AIOps Stage 3 - Stopping Services${NC}"
echo -e "${YELLOW}========================================${NC}"

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

# Stop the services
echo ""
echo -e "${YELLOW}Stopping AIOps Stage 3 services...${NC}"

docker-compose -f docker-compose-aiops.yml down

echo -e "${GREEN}✓ AIOps Stage 3 services stopped${NC}"

# Display stopped services
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AIOps Stage 3 - Services Stopped${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Stage 1 and Stage 2 services are still running."
echo "To stop all services, run: docker-compose down"
echo ""