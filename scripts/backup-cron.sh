#!/usr/bin/env bash
# Setup cron jobs for inferbox backups
# Usage: sudo ./scripts/backup-cron.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="/var/log/inferbox-backup.log"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Ensure backup directory exists
mkdir -p /opt/inferbox/backups
chmod 755 /opt/inferbox/backups

# Ensure log file exists
touch "$LOG_FILE"
chmod 644 "$LOG_FILE"

# Make backup scripts executable
chmod +x "${PROJECT_ROOT}/scripts/backup_db.sh"
chmod +x "${PROJECT_ROOT}/scripts/backup-rotation.sh"

echo "Setting up inferbox backup cron jobs..."

# Create temporary cron file
TEMP_CRON=$(mktemp)

# Get existing crontab (excluding old inferbox entries)
(crontab -l 2>/dev/null || echo "") | grep -v "inferbox" > "$TEMP_CRON" || true

# Add new cron entries
cat >> "$TEMP_CRON" << EOF

# inferbox automated backups
# Daily backup at 2:00 AM
0 2 * * * cd ${PROJECT_ROOT} && ${PROJECT_ROOT}/scripts/backup_db.sh >> ${LOG_FILE} 2>&1

# Weekly full backup (Sunday at 3:00 AM)
0 3 * * 0 cd ${PROJECT_ROOT} && ${PROJECT_ROOT}/scripts/backup_db.sh --weekly >> ${LOG_FILE} 2>&1

EOF

# Install new crontab
crontab "$TEMP_CRON"
rm -f "$TEMP_CRON"

echo "Cron jobs installed successfully!"
echo ""
echo "Backup schedule:"
echo "  - Daily backup:  Every day at 2:00 AM (retention: 7 days)"
echo "  - Weekly backup: Every Sunday at 3:00 AM (retention: 90 days)"
echo ""
echo "Backup location: /opt/inferbox/backups"
echo "Log file: ${LOG_FILE}"
echo ""
echo "To view current crontab: crontab -l"
echo "To view backup log: tail -f ${LOG_FILE}"
echo ""
echo "Manual backup commands:"
echo "  Daily:  ${PROJECT_ROOT}/scripts/backup_db.sh"
echo "  Weekly: ${PROJECT_ROOT}/scripts/backup_db.sh --weekly"

exit 0
