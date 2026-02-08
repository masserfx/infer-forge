#!/usr/bin/env bash
# PostgreSQL restore script for INFER FORGE
# Usage: ./scripts/restore_db.sh /path/to/backup.sql.gz [/path/to/uploads-backup.tar.gz]

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/opt/infer-forge/backups}"
LOG_FILE="${LOG_FILE:-/var/log/infer-forge-backup.log}"

# Arguments
BACKUP_FILE="${1:-}"
UPLOADS_BACKUP="${2:-}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] RESTORE: $*" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check arguments
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz> [uploads_backup.tar.gz]"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "  (none found)"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    error_exit "Backup file not found: $BACKUP_FILE"
fi

# Load environment variables
if [ -f "${PROJECT_ROOT}/.env.prod" ]; then
    set -a
    source "${PROJECT_ROOT}/.env.prod"
    set +a
fi

DB_NAME="${POSTGRES_DB:-infer_forge}"
DB_USER="${POSTGRES_USER:-infer}"

log "========================================="
log "INFER FORGE Database Restore"
log "========================================="
log "Backup file: ${BACKUP_FILE}"
if [ -n "$UPLOADS_BACKUP" ] && [ -f "$UPLOADS_BACKUP" ]; then
    log "Uploads backup: ${UPLOADS_BACKUP}"
fi
log "Database: ${DB_NAME}"
log "========================================="

# Change to project root
cd "$PROJECT_ROOT" || error_exit "Failed to change to project root: $PROJECT_ROOT"

# Check if Docker Compose is running
if ! docker compose -f docker-compose.prod.yml ps db | grep -q "Up"; then
    error_exit "Database container is not running. Start it with: docker compose -f docker-compose.prod.yml up -d db"
fi

# Confirmation prompt
echo ""
echo "WARNING: This will:"
echo "  1. Create a safety backup of the current database"
echo "  2. Drop and recreate the database '${DB_NAME}'"
echo "  3. Restore from: $(basename "$BACKUP_FILE")"
if [ -n "$UPLOADS_BACKUP" ] && [ -f "$UPLOADS_BACKUP" ]; then
    echo "  4. Restore uploads from: $(basename "$UPLOADS_BACKUP")"
fi
echo "  5. Run Alembic migrations"
echo ""
read -p "Type 'yes' to continue: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log "Restore aborted by user"
    exit 0
fi

# 1. Create safety backup of current database
SAFETY_BACKUP="${BACKUP_DIR}/safety-backup-$(date +%Y-%m-%d-%H%M%S).sql.gz"
log "Creating safety backup: ${SAFETY_BACKUP}"

mkdir -p "$BACKUP_DIR"

if docker compose -f docker-compose.prod.yml exec -T db pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    | gzip > "$SAFETY_BACKUP"; then

    SAFETY_SIZE=$(du -h "$SAFETY_BACKUP" | cut -f1)
    log "Safety backup complete: ${SAFETY_SIZE}"
else
    error_exit "Failed to create safety backup"
fi

# 2. Drop and recreate database
log "Dropping database '${DB_NAME}'..."
if ! docker compose -f docker-compose.prod.yml exec -T db dropdb -U "$DB_USER" --if-exists "$DB_NAME"; then
    error_exit "Failed to drop database"
fi

log "Creating database '${DB_NAME}'..."
if ! docker compose -f docker-compose.prod.yml exec -T db createdb -U "$DB_USER" "$DB_NAME"; then
    error_exit "Failed to create database"
fi

# 3. Restore from backup
log "Restoring from backup..."

# Detect if backup is gzipped
if [[ "$BACKUP_FILE" == *.gz ]]; then
    log "Detected gzip compression, decompressing..."
    if ! gunzip -c "$BACKUP_FILE" | docker compose -f docker-compose.prod.yml exec -T db psql -U "$DB_USER" -d "$DB_NAME" -q; then
        log "ERROR: Restore failed! Restoring from safety backup..."
        gunzip -c "$SAFETY_BACKUP" | docker compose -f docker-compose.prod.yml exec -T db psql -U "$DB_USER" -d "$DB_NAME" -q || true
        error_exit "Restore failed and safety backup restored"
    fi
else
    log "Detected plain SQL file..."
    if ! docker compose -f docker-compose.prod.yml exec -T db psql -U "$DB_USER" -d "$DB_NAME" -q < "$BACKUP_FILE"; then
        log "ERROR: Restore failed! Restoring from safety backup..."
        gunzip -c "$SAFETY_BACKUP" | docker compose -f docker-compose.prod.yml exec -T db psql -U "$DB_USER" -d "$DB_NAME" -q || true
        error_exit "Restore failed and safety backup restored"
    fi
fi

log "Database restore complete"

# 4. Restore uploads if provided
if [ -n "$UPLOADS_BACKUP" ] && [ -f "$UPLOADS_BACKUP" ]; then
    log "Restoring uploads volume..."

    # Extract uploads to temporary directory
    TEMP_UPLOADS=$(mktemp -d)
    if tar -xzf "$UPLOADS_BACKUP" -C "$TEMP_UPLOADS"; then
        # Copy to backend container
        # Find the actual uploads directory in the extracted archive
        UPLOADS_SOURCE=$(find "$TEMP_UPLOADS" -type d -name "uploads-*" -o -name "uploads" | head -n1)

        if [ -n "$UPLOADS_SOURCE" ] && [ -d "$UPLOADS_SOURCE" ]; then
            docker compose -f docker-compose.prod.yml cp "$UPLOADS_SOURCE/." backend:/app/uploads/ 2>/dev/null || \
                log "WARNING: Failed to copy uploads to container"
            log "Uploads restore complete"
        else
            log "WARNING: Could not find uploads directory in archive"
        fi

        rm -rf "$TEMP_UPLOADS"
    else
        log "WARNING: Failed to extract uploads backup"
    fi
fi

# 5. Run Alembic migrations
log "Running Alembic migrations..."
if docker compose -f docker-compose.prod.yml exec -T backend bash -c "cd /app && alembic upgrade head"; then
    log "Migrations complete"
else
    log "WARNING: Migrations failed - you may need to run them manually"
fi

# 6. Summary
log "========================================="
log "Restore completed successfully!"
log "========================================="
log "Restored from: $(basename "$BACKUP_FILE")"
log "Safety backup: ${SAFETY_BACKUP}"
log ""
log "To verify the restore:"
log "  docker compose -f docker-compose.prod.yml exec db psql -U ${DB_USER} -d ${DB_NAME} -c '\\dt'"
log ""
log "If something went wrong, restore the safety backup:"
log "  ${PROJECT_ROOT}/scripts/restore_db.sh ${SAFETY_BACKUP}"
log "========================================="

exit 0
