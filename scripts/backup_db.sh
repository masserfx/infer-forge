#!/usr/bin/env bash
# PostgreSQL backup script for inferbox
# Usage: ./scripts/backup_db.sh [--weekly]
# Requires: docker compose, POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD env vars

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/opt/inferbox/backups}"
LOG_FILE="${LOG_FILE:-/var/log/inferbox-backup.log}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
WEEKLY_RETENTION_DAYS="${WEEKLY_RETENTION_DAYS:-90}"

# Check if this is a weekly backup
WEEKLY_BACKUP=false
if [ "${1:-}" = "--weekly" ]; then
    WEEKLY_BACKUP=true
    RETENTION_DAYS="$WEEKLY_RETENTION_DAYS"
fi

# Timestamp format: YYYY-MM-DD-HHMMSS
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
DATE_ONLY=$(date +%Y-%m-%d)

# Backup file names
if [ "$WEEKLY_BACKUP" = true ]; then
    DB_BACKUP_FILE="${BACKUP_DIR}/inferbox-weekly-${TIMESTAMP}.sql.gz"
    UPLOADS_BACKUP_DIR="${BACKUP_DIR}/uploads-weekly-${DATE_ONLY}"
else
    DB_BACKUP_FILE="${BACKUP_DIR}/inferbox-backup-${TIMESTAMP}.sql.gz"
    UPLOADS_BACKUP_DIR="${BACKUP_DIR}/uploads-${DATE_ONLY}"
fi

# Load environment variables
if [ -f "${PROJECT_ROOT}/.env.prod" ]; then
    set -a
    source "${PROJECT_ROOT}/.env.prod"
    set +a
fi

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Create backup directory
mkdir -p "$BACKUP_DIR" || error_exit "Failed to create backup directory: $BACKUP_DIR"

# Create log file if not exists
touch "$LOG_FILE" 2>/dev/null || true

log "========================================="
if [ "$WEEKLY_BACKUP" = true ]; then
    log "Starting WEEKLY backup"
else
    log "Starting DAILY backup"
fi
log "========================================="

# Change to project root
cd "$PROJECT_ROOT" || error_exit "Failed to change to project root: $PROJECT_ROOT"

# Check if Docker Compose is running
if ! docker compose -f docker-compose.prod.yml ps db | grep -q "Up"; then
    error_exit "Database container is not running"
fi

# 1. Backup PostgreSQL database
log "Backing up PostgreSQL database to: ${DB_BACKUP_FILE}"
if docker compose -f docker-compose.prod.yml exec -T db pg_dump \
    -U "${POSTGRES_USER:-infer}" \
    -d "${POSTGRES_DB:-infer_forge}" \
    --no-owner \
    --no-privileges \
    | gzip > "$DB_BACKUP_FILE"; then

    DB_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
    log "Database backup complete: ${DB_SIZE}"
else
    error_exit "Database backup failed"
fi

# 2. Backup uploads volume
log "Backing up uploads volume to: ${UPLOADS_BACKUP_DIR}"
if docker compose -f docker-compose.prod.yml cp backend:/app/uploads "$UPLOADS_BACKUP_DIR" 2>/dev/null; then
    # Compress uploads directory
    tar -czf "${UPLOADS_BACKUP_DIR}.tar.gz" -C "$BACKUP_DIR" "$(basename "$UPLOADS_BACKUP_DIR")" 2>/dev/null || true
    rm -rf "$UPLOADS_BACKUP_DIR" 2>/dev/null || true

    if [ -f "${UPLOADS_BACKUP_DIR}.tar.gz" ]; then
        UPLOADS_SIZE=$(du -h "${UPLOADS_BACKUP_DIR}.tar.gz" | cut -f1)
        log "Uploads backup complete: ${UPLOADS_SIZE}"
    else
        log "WARNING: Uploads backup compression failed"
    fi
else
    log "WARNING: Uploads volume backup failed (container may not have /app/uploads)"
fi

# 3. Run backup rotation script
if [ -f "${PROJECT_ROOT}/scripts/backup-rotation.sh" ]; then
    log "Running backup rotation..."
    bash "${PROJECT_ROOT}/scripts/backup-rotation.sh" "$WEEKLY_BACKUP" || log "WARNING: Backup rotation failed"
else
    # Fallback: simple retention by days
    log "Removing backups older than ${RETENTION_DAYS} days..."
    if [ "$WEEKLY_BACKUP" = true ]; then
        find "$BACKUP_DIR" -name "inferbox-weekly-*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
        find "$BACKUP_DIR" -name "uploads-weekly-*.tar.gz" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
    else
        find "$BACKUP_DIR" -name "inferbox-backup-*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
        find "$BACKUP_DIR" -name "uploads-*.tar.gz" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
    fi
fi

# 4. Summary
log "========================================="
log "Backup completed successfully!"
log "Database: ${DB_BACKUP_FILE}"
if [ -f "${UPLOADS_BACKUP_DIR}.tar.gz" ]; then
    log "Uploads: ${UPLOADS_BACKUP_DIR}.tar.gz"
fi
log "========================================="
log "Remaining backups in ${BACKUP_DIR}:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | awk '{print $9, $5}' | tee -a "$LOG_FILE" || log "  (no database backups)"
ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | awk '{print $9, $5}' | tee -a "$LOG_FILE" || log "  (no upload backups)"
log "========================================="

exit 0
