#!/bin/bash

# test-monitoring.sh
# Health check pro monitoring služby INFER FORGE

set -e

# Barvy pro výstup
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Počítadla
TOTAL=0
HEALTHY=0

# Timeout pro curl
TIMEOUT=5

echo "======================================"
echo "INFER FORGE Monitoring Health Check"
echo "======================================"
echo ""

# Funkce pro test služby
test_service() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}

    TOTAL=$((TOTAL + 1))

    if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_status" ]; then
            echo -e "[${GREEN}✓${NC}] $name - OK (HTTP $response)"
            HEALTHY=$((HEALTHY + 1))
        else
            echo -e "[${RED}✗${NC}] $name - FAIL (HTTP $response, očekáváno $expected_status)"
        fi
    else
        echo -e "[${RED}✗${NC}] $name - NEDOSTUPNÝ (timeout nebo connection error)"
    fi
}

# Test jednotlivých služeb
test_service "Prometheus" "http://localhost:9090/-/healthy"
test_service "Grafana" "http://localhost:3002/api/health"
test_service "Flower (Celery UI)" "http://localhost:5555/"
test_service "Alertmanager" "http://localhost:9093/-/healthy"
test_service "Postgres Exporter" "http://localhost:9187/metrics"
test_service "Redis Exporter" "http://localhost:9121/metrics"
test_service "Backend Metrics" "http://localhost:8000/metrics"

# Souhrn
echo ""
echo "======================================"
if [ $HEALTHY -eq $TOTAL ]; then
    echo -e "${GREEN}Výsledek: $HEALTHY/$TOTAL služeb je zdravých${NC}"
    exit 0
else
    echo -e "${RED}Výsledek: $HEALTHY/$TOTAL služeb je zdravých${NC}"
    exit 1
fi
