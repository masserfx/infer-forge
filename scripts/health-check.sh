#!/bin/bash
# Komplexní health check pro INFER FORGE produkční stack

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_RESET='\033[0m'

success() {
    echo -e "${COLOR_GREEN}✅ $1${COLOR_RESET}"
}

error() {
    echo -e "${COLOR_RED}❌ $1${COLOR_RESET}"
}

warning() {
    echo -e "${COLOR_YELLOW}⚠️  $1${COLOR_RESET}"
}

echo "=== INFER FORGE Health Check ==="
echo ""

# 1. Docker containers
echo "1️⃣  Kontrola Docker containers..."
if command -v docker &> /dev/null; then
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        success "Docker containers běží"
        docker compose -f "$COMPOSE_FILE" ps
    else
        error "Docker containers neběží"
        exit 1
    fi
else
    warning "Docker není nainstalován"
fi
echo ""

# 2. Backend API
echo "2️⃣  Kontrola Backend API..."
if curl -sf "$BACKEND_URL/health" > /dev/null 2>&1; then
    success "Backend API dostupné ($BACKEND_URL)"

    # Detailní health check
    health_response=$(curl -s "$BACKEND_URL/health")
    echo "$health_response" | jq '.' 2>/dev/null || echo "$health_response"
else
    error "Backend API nedostupné ($BACKEND_URL)"
    exit 1
fi
echo ""

# 3. Database
echo "3️⃣  Kontrola PostgreSQL..."
if curl -sf "$BACKEND_URL/health/db" > /dev/null 2>&1; then
    success "PostgreSQL připojena"
else
    error "PostgreSQL nedostupná"
fi
echo ""

# 4. Redis
echo "4️⃣  Kontrola Redis..."
if curl -sf "$BACKEND_URL/health/redis" > /dev/null 2>&1; then
    success "Redis připojen"
else
    error "Redis nedostupný"
fi
echo ""

# 5. Frontend
echo "5️⃣  Kontrola Frontend..."
if curl -sf "$FRONTEND_URL" > /dev/null 2>&1; then
    success "Frontend dostupný ($FRONTEND_URL)"
else
    warning "Frontend nedostupný ($FRONTEND_URL)"
fi
echo ""

# 6. Celery workers
echo "6️⃣  Kontrola Celery workers..."
if docker compose -f "$COMPOSE_FILE" ps celery-worker | grep -q "Up"; then
    success "Celery worker běží"

    # Počet aktivních tasků
    worker_inspect=$(docker compose -f "$COMPOSE_FILE" exec -T celery-worker \
        celery -A app.core.celery_app inspect active 2>/dev/null || echo "{}")

    if [[ "$worker_inspect" == "{}" ]]; then
        echo "  Žádné aktivní tasky"
    else
        echo "  Aktivní tasky:"
        echo "$worker_inspect" | jq '.' 2>/dev/null || echo "$worker_inspect"
    fi
else
    warning "Celery worker neběží"
fi
echo ""

# 7. Disk usage
echo "7️⃣  Kontrola disk usage..."
if command -v docker &> /dev/null; then
    echo "Docker volumes:"
    docker system df -v | grep -E "VOLUME NAME|infer-forge" || true
fi
echo ""

# 8. Memory usage
echo "8️⃣  Kontrola memory usage..."
if command -v docker &> /dev/null; then
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | \
        grep -E "NAME|infer-forge" || true
fi
echo ""

# 9. Recent logs (errors)
echo "9️⃣  Poslední chyby v logs..."
if docker compose -f "$COMPOSE_FILE" logs --tail=50 backend 2>/dev/null | \
    grep -iE "error|exception|critical" | tail -5; then
    warning "Nalezeny errory v logs"
else
    success "Žádné errory v posledních 50 řádcích"
fi
echo ""

# 10. API verze
echo "🔟 API verze..."
version=$(curl -s "$BACKEND_URL/" | jq -r '.version // "unknown"' 2>/dev/null || echo "unknown")
success "Verze: $version"
echo ""

echo "=== Health Check dokončen ==="
echo ""
echo "📊 Shrnutí:"
echo "  Backend:  $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo "  Compose:  $COMPOSE_FILE"
echo ""
echo "Pro detailní logy:"
echo "  docker compose -f $COMPOSE_FILE logs -f backend"
