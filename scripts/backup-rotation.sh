#!/usr/bin/env bash
# Backup rotation script for INFER FORGE
# Retention policy: 7 daily, 4 weekly, 3 monthly backups
# Usage: ./scripts/backup-rotation.sh [weekly]

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/infer-forge/backups}"
LOG_FILE="${LOG_FILE:-/var/log/infer-forge-backup.log}"
WEEKLY_BACKUP="${1:-false}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ROTATION: $*" | tee -a "$LOG_FILE"
}

log "Starting backup rotation..."

# 1. Keep 7 daily backups (delete older)
DAILY_BACKUPS=$(find "$BACKUP_DIR" -name "infer-forge-backup-*.sql.gz" -type f -mtime -7 | wc -l)
DAILY_TO_DELETE=$(find "$BACKUP_DIR" -name "infer-forge-backup-*.sql.gz" -type f -mtime +7)

if [ -n "$DAILY_TO_DELETE" ]; then
    log "Removing old daily backups (keeping last 7 days):"
    echo "$DAILY_TO_DELETE" | while read -r file; do
        log "  - $(basename "$file")"
        rm -f "$file"
    done
    # Also remove corresponding upload backups
    find "$BACKUP_DIR" -name "uploads-*.tar.gz" -type f -mtime +7 -delete 2>/dev/null || true
else
    log "No old daily backups to remove (${DAILY_BACKUPS} backups < 7 days old)"
fi

# 2. Keep 4 weekly backups (delete older)
WEEKLY_BACKUPS=$(find "$BACKUP_DIR" -name "infer-forge-weekly-*.sql.gz" -type f -mtime -28 | wc -l)
WEEKLY_TO_DELETE=$(find "$BACKUP_DIR" -name "infer-forge-weekly-*.sql.gz" -type f -mtime +28)

if [ -n "$WEEKLY_TO_DELETE" ]; then
    log "Removing old weekly backups (keeping last 4 weeks):"
    echo "$WEEKLY_TO_DELETE" | while read -r file; do
        log "  - $(basename "$file")"
        rm -f "$file"
    done
    # Also remove corresponding upload backups
    find "$BACKUP_DIR" -name "uploads-weekly-*.tar.gz" -type f -mtime +28 -delete 2>/dev/null || true
else
    log "No old weekly backups to remove (${WEEKLY_BACKUPS} backups < 28 days old)"
fi

# 3. Keep 3 monthly backups (first weekly of each month, keep for 90 days)
# Find all weekly backups older than 90 days and delete
MONTHLY_TO_DELETE=$(find "$BACKUP_DIR" -name "infer-forge-weekly-*.sql.gz" -type f -mtime +90)

if [ -n "$MONTHLY_TO_DELETE" ]; then
    log "Removing weekly backups older than 90 days:"
    echo "$MONTHLY_TO_DELETE" | while read -r file; do
        log "  - $(basename "$file")"
        rm -f "$file"
    done
    find "$BACKUP_DIR" -name "uploads-weekly-*.tar.gz" -type f -mtime +90 -delete 2>/dev/null || true
else
    log "No backups older than 90 days to remove"
fi

# 4. Summary
log "Rotation complete. Current backup counts:"
DAILY_COUNT=$(find "$BACKUP_DIR" -name "infer-forge-backup-*.sql.gz" -type f | wc -l)
WEEKLY_COUNT=$(find "$BACKUP_DIR" -name "infer-forge-weekly-*.sql.gz" -type f | wc -l)
log "  Daily backups: ${DAILY_COUNT}"
log "  Weekly backups: ${WEEKLY_COUNT}"

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "unknown")
log "  Total backup size: ${TOTAL_SIZE}"

exit 0
