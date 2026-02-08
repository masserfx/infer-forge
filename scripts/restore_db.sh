#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/restore_db.sh /path/to/backup.sql.gz

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: File '$BACKUP_FILE' not found"
    exit 1
fi

# Load env
source .env.prod 2>/dev/null || true

DB_NAME="${POSTGRES_DB:-infer_forge}"
DB_USER="${POSTGRES_USER:-infer}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo "WARNING: This will DROP and recreate database '$DB_NAME'"
read -p "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo "Dropping database..."
PGPASSWORD="${POSTGRES_PASSWORD}" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME"

echo "Creating database..."
PGPASSWORD="${POSTGRES_PASSWORD}" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

echo "Restoring from '$BACKUP_FILE'..."
gunzip -c "$BACKUP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q

echo "Running Alembic migrations..."
cd backend && uv run alembic upgrade head

echo "Restore complete!"
