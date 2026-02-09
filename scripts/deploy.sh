#!/usr/bin/env bash
# deploy.sh — Automated production deployment for INFER FORGE
# Usage: ./scripts/deploy.sh [--skip-tests] [--skip-build]
#
# Connects to Hetzner server, pulls latest, rebuilds, migrates, verifies.

set -euo pipefail

# ─── Config ─────────────────────────────────────────────────
SSH_HOST="hetzner-root"
PROJ_DIR="/home/leos/infer-forge"
COMPOSE="docker compose -f docker-compose.prod.yml"
SERVICES="backend frontend celery-worker celery-beat"
BUILD_SERVICES="backend frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SKIP_TESTS=false
SKIP_BUILD=false

for arg in "$@"; do
  case $arg in
    --skip-tests) SKIP_TESTS=true ;;
    --skip-build) SKIP_BUILD=true ;;
  esac
done

log()  { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# ─── 1. Pre-flight (local) ─────────────────────────────────
log "Pre-flight kontroly..."

if ! git diff --quiet || ! git diff --cached --quiet; then
  warn "Existují uncommitted změny! Commitni před deployem."
  git status --short
  exit 1
fi

COMMIT_HASH=$(git log --oneline -1 --format="%h")
COMMIT_MSG=$(git log --oneline -1 --format="%s")
log "Deploy commit: ${COMMIT_HASH} — ${COMMIT_MSG}"

if [ "$SKIP_TESTS" = false ]; then
  log "Spouštím backend testy..."
  (cd backend && uv run pytest tests/ -x -q) || fail "Backend testy selhaly!"

  log "Spouštím frontend build..."
  (cd frontend && npm run build) || fail "Frontend build selhal!"
else
  warn "Testy přeskočeny (--skip-tests)"
fi

# ─── 2. Push ────────────────────────────────────────────────
log "Push na origin/main..."
git push origin main || fail "Push selhal!"

# ─── 3. Deploy na server ───────────────────────────────────
log "Připojuji se na ${SSH_HOST}..."

ssh "$SSH_HOST" bash -s -- "$PROJ_DIR" "$SKIP_BUILD" << 'REMOTE_SCRIPT'
set -euo pipefail
PROJ_DIR="$1"
SKIP_BUILD="$2"
COMPOSE="docker compose -f docker-compose.prod.yml"

cd "$PROJ_DIR"
echo "[REMOTE] git pull..."
git pull origin main

if [ "$SKIP_BUILD" = false ]; then
  echo "[REMOTE] Building backend + frontend..."
  $COMPOSE build backend frontend
fi

echo "[REMOTE] Restarting services..."
$COMPOSE up -d backend frontend celery-worker celery-beat

echo "[REMOTE] Waiting for containers to be healthy..."
sleep 8

echo "[REMOTE] Running Alembic migrations..."
$COMPOSE exec -T backend alembic upgrade head

echo "[REMOTE] Smoke tests..."
FAILURES=0

if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
  echo "[SMOKE] Backend health: OK"
else
  echo "[SMOKE] Backend health: FAIL"
  FAILURES=$((FAILURES + 1))
fi

if curl -sf http://localhost:8000/api/v1/orchestrace/stats > /dev/null 2>&1; then
  echo "[SMOKE] API /orchestrace/stats: OK"
else
  echo "[SMOKE] API /orchestrace/stats: FAIL"
  FAILURES=$((FAILURES + 1))
fi

if curl -sf http://localhost:3000 -o /dev/null 2>&1; then
  echo "[SMOKE] Frontend: OK"
else
  echo "[SMOKE] Frontend: FAIL"
  FAILURES=$((FAILURES + 1))
fi

echo ""
echo "=== Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}" | grep infer-forge

echo ""
echo "=== Safety Switches ==="
grep -E "^(EMAIL_SENDING_ENABLED|IMAP_POLLING_ENABLED)" "$PROJ_DIR/.env" 2>/dev/null || echo "(not found in .env)"

if [ $FAILURES -gt 0 ]; then
  echo ""
  echo "[DEPLOY] UPOZORNĚNÍ: $FAILURES smoke test(ů) selhalo!"
  exit 1
fi

echo ""
echo "[DEPLOY] Deployment úspěšný!"
REMOTE_SCRIPT

log "Deploy dokončen: ${COMMIT_HASH} — ${COMMIT_MSG}"
