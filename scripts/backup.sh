#!/usr/bin/env bash
# Daily SQLite backup (rule 3.5).
#
# Install as a cron job:
#   chmod +x scripts/backup.sh
#   crontab -e
#   0 3 * * * /home/ubuntu/shop_bot/scripts/backup.sh >> /home/ubuntu/backup.log 2>&1

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_FILE="${DB_PATH:-$APP_DIR/shop.db}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_FILE" ]; then
  echo "$(date '+%F %T') ERROR: database not found at $DB_FILE"
  exit 1
fi

STAMP="$(date '+%Y%m%d_%H%M%S')"
TARGET="$BACKUP_DIR/shop_$STAMP.db"

# .backup is safe on a live database — unlike cp, it respects WAL mode.
sqlite3 "$DB_FILE" ".backup '$TARGET'"
gzip -f "$TARGET"

# Retention.
find "$BACKUP_DIR" -name 'shop_*.db.gz' -mtime "+$KEEP_DAYS" -delete

echo "$(date '+%F %T') backup OK: ${TARGET}.gz"
