#!/usr/bin/env bash
# PostgreSQL backup script for INFER FORGE
# Usage: ./scripts/backup_db.sh
# Requires: POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD env vars

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/infer_forge_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Starting backup: ${BACKUP_FILE}"
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER:-infer}" \
    -d "${POSTGRES_DB:-infer_forge}" \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_FILE"

echo "Backup complete: $(du -h "$BACKUP_FILE" | cut -f1)"

# Cleanup old backups
echo "Removing backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "infer_forge_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "Done. Remaining backups:"
ls -lh "$BACKUP_DIR"/infer_forge_*.sql.gz 2>/dev/null || echo "  (none)"
