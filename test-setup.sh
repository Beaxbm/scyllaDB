#!/bin/bash

# Gauge IoT Infrastructure Test Script

echo "🚀 Gauge IoT Infrastructure Test"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test connectivity
test_endpoint() {
    local url=$1
    local name=$2
    
    echo -n "Testing $name... "
    if curl -s -f "$url" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Start basic infrastructure
echo -e "\n${BLUE}1. Starting core infrastructure (Home Assistant + MQTT)${NC}"
docker-compose up -d
sleep 5

# Test basic services
echo -e "\n${BLUE}2. Testing core services${NC}"
test_endpoint "http://localhost:8123" "Home Assistant"
test_endpoint "http://localhost:1883" "MQTT Broker" || echo "   (Connection refused is expected for HTTP to MQTT)"

# Start ScyllaDB infrastructure  
echo -e "\n${BLUE}3. Starting ScyllaDB infrastructure${NC}"
docker-compose -f docker-compose-scylla.yml up -d

echo -e "\n${YELLOW}⏳ Waiting for ScyllaDB to initialize (60 seconds)...${NC}"
sleep 60

# Test ScyllaDB services
echo -e "\n${BLUE}4. Testing ScyllaDB services${NC}"
test_endpoint "http://localhost:9042" "ScyllaDB CQL" || echo "   (Connection refused is expected for HTTP to CQL)"
test_endpoint "http://localhost:8001/health" "ScyllaDB API"

# Show running containers
echo -e "\n${BLUE}5. Container Status${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test data flow
echo -e "\n${BLUE}6. Testing data ingestion${NC}"
echo "Monitoring MQTT traffic for 10 seconds..."
timeout 10 docker exec mosquitto mosquitto_sub -h localhost -t "ha/statestream/#" -C 5 || echo "No MQTT messages detected"

echo -e "\n${BLUE}7. API Comparison${NC}"
echo "ScyllaDB API (port 8001):"
curl -s http://localhost:8001/sensors | jq -r '. | length' 2>/dev/null | xargs -I {} echo "  📊 {} sensors discovered"

echo -e "\n${GREEN}✅ Setup complete!${NC}"
echo -e "\n${BLUE}Access Points:${NC}"
echo "  🏠 Home Assistant:    http://localhost:8123"
echo "  ⚡ ScyllaDB API:      http://localhost:8001"
echo "  📊 ScyllaDB Metrics:  http://localhost:19042/metrics"

echo -e "\n${BLUE}Quick API Tests:${NC}"
echo "  curl http://localhost:8001/health"
echo "  curl http://localhost:8001/sensors" 
echo "  curl http://localhost:8001/sensors/domain/sensor"

echo -e "\n${BLUE}Logs:${NC}"
echo "  docker-compose logs -f homeassistant"
echo "  docker-compose -f docker-compose-scylla.yml logs -f scylla-ingestor"

echo -e "\n${YELLOW}💡 Let the system run for a few minutes to collect sensor data!${NC}"