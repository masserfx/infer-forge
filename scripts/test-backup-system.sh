#!/usr/bin/env bash
# Test script for INFER FORGE backup system
# Usage: ./scripts/test-backup-system.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASSED=0
FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_info() {
    echo "ℹ $1"
}

echo "========================================="
echo "INFER FORGE Backup System Test"
echo "========================================="
echo ""

# 1. Check if scripts exist
log_info "Checking if backup scripts exist..."
for script in backup_db.sh backup-rotation.sh backup-cron.sh restore_db.sh; do
    if [ -f "${PROJECT_ROOT}/scripts/${script}" ]; then
        log_pass "Script exists: ${script}"
    else
        log_fail "Script missing: ${script}"
    fi
done

# 2. Check script permissions
log_info ""
log_info "Checking script permissions..."
for script in backup_db.sh backup-rotation.sh backup-cron.sh restore_db.sh; do
    if [ -x "${PROJECT_ROOT}/scripts/${script}" ]; then
        log_pass "Executable: ${script}"
    else
        log_fail "Not executable: ${script} (run: chmod +x scripts/${script})"
    fi
done

# 3. Check Docker Compose file
log_info ""
log_info "Checking Docker Compose configuration..."
if [ -f "${PROJECT_ROOT}/docker-compose.prod.yml" ]; then
    log_pass "docker-compose.prod.yml exists"

    # Check if db service is defined
    if grep -q "^  db:" "${PROJECT_ROOT}/docker-compose.prod.yml"; then
        log_pass "db service is defined in docker-compose.prod.yml"
    else
        log_fail "db service not found in docker-compose.prod.yml"
    fi
else
    log_fail "docker-compose.prod.yml not found"
fi

# 4. Check .env.prod file
log_info ""
log_info "Checking environment configuration..."
if [ -f "${PROJECT_ROOT}/.env.prod" ]; then
    log_pass ".env.prod exists"

    # Check required variables
    source "${PROJECT_ROOT}/.env.prod" 2>/dev/null || true
    if [ -n "${POSTGRES_DB:-}" ]; then
        log_pass "POSTGRES_DB is set"
    else
        log_warn "POSTGRES_DB not set in .env.prod"
    fi

    if [ -n "${POSTGRES_USER:-}" ]; then
        log_pass "POSTGRES_USER is set"
    else
        log_warn "POSTGRES_USER not set in .env.prod"
    fi

    if [ -n "${POSTGRES_PASSWORD:-}" ]; then
        log_pass "POSTGRES_PASSWORD is set"
    else
        log_warn "POSTGRES_PASSWORD not set in .env.prod"
    fi
else
    log_warn ".env.prod not found (create from .env.prod.example)"
fi

# 5. Check if Docker is running
log_info ""
log_info "Checking Docker status..."
if command -v docker &> /dev/null; then
    log_pass "Docker is installed"

    if docker ps &> /dev/null; then
        log_pass "Docker daemon is running"

        # Check if db container exists
        cd "$PROJECT_ROOT"
        if docker compose -f docker-compose.prod.yml ps db 2>/dev/null | grep -q "db"; then
            if docker compose -f docker-compose.prod.yml ps db | grep -q "Up"; then
                log_pass "Database container is running"
            else
                log_warn "Database container exists but is not running"
            fi
        else
            log_warn "Database container not found (not deployed yet)"
        fi
    else
        log_warn "Docker daemon is not running"
    fi
else
    log_warn "Docker is not installed (required for production)"
fi

# 6. Check backup directory (if on production server)
log_info ""
log_info "Checking backup directory..."
if [ -d "/opt/infer-forge/backups" ]; then
    log_pass "Backup directory exists: /opt/infer-forge/backups"

    # Check permissions
    if [ -w "/opt/infer-forge/backups" ]; then
        log_pass "Backup directory is writable"
    else
        log_warn "Backup directory is not writable"
    fi

    # Count existing backups
    BACKUP_COUNT=$(find /opt/infer-forge/backups -name "*.sql.gz" 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        log_pass "Found ${BACKUP_COUNT} existing backup(s)"
    else
        log_warn "No backups found (not created yet)"
    fi
else
    log_warn "Backup directory /opt/infer-forge/backups does not exist (will be created on first backup)"
fi

# 7. Check log file
log_info ""
log_info "Checking log file..."
if [ -f "/var/log/infer-forge-backup.log" ]; then
    log_pass "Log file exists: /var/log/infer-forge-backup.log"

    # Check if writable
    if [ -w "/var/log/infer-forge-backup.log" ]; then
        log_pass "Log file is writable"
    else
        log_warn "Log file is not writable"
    fi

    # Show last backup entry
    LAST_BACKUP=$(grep "Backup completed successfully" /var/log/infer-forge-backup.log 2>/dev/null | tail -1 || echo "")
    if [ -n "$LAST_BACKUP" ]; then
        log_pass "Last successful backup: ${LAST_BACKUP}"
    else
        log_warn "No successful backups in log yet"
    fi
else
    log_warn "Log file /var/log/infer-forge-backup.log does not exist (will be created on first backup)"
fi

# 8. Check cron jobs (if running as root or with sudo)
log_info ""
log_info "Checking cron jobs..."
if [ "$EUID" -eq 0 ]; then
    CRON_DAILY=$(crontab -l 2>/dev/null | grep -c "backup_db.sh" || echo "0")
    CRON_WEEKLY=$(crontab -l 2>/dev/null | grep -c "backup_db.sh --weekly" || echo "0")

    if [ "$CRON_DAILY" -gt 0 ]; then
        log_pass "Daily backup cron job is installed"
    else
        log_warn "Daily backup cron job not found (run: sudo ./scripts/backup-cron.sh)"
    fi

    if [ "$CRON_WEEKLY" -gt 0 ]; then
        log_pass "Weekly backup cron job is installed"
    else
        log_warn "Weekly backup cron job not found (run: sudo ./scripts/backup-cron.sh)"
    fi
else
    log_warn "Not running as root - skipping cron check (run with sudo to check cron jobs)"
fi

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Passed: ${PASSED}${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: ${FAILED}${NC}"
fi
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Install cron jobs: sudo ./scripts/backup-cron.sh"
    echo "  2. Test manual backup: ./scripts/backup_db.sh"
    echo "  3. Monitor logs: tail -f /var/log/infer-forge-backup.log"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please fix the issues above.${NC}"
    exit 1
fi
