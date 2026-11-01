#!/usr/bin/env bash
set -euo pipefail

# Run on the production host after loading /opt/huance/.env.
# Creates an application archive and a PostgreSQL custom-format dump.

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
BACKUP_DIR="${BACKUP_DIR:-/opt/huance/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
pg_dump --format=custom --file="$BACKUP_DIR/db_${STAMP}.dump" "$POSTGRES_DB"
tar --exclude='./media/*' -czf "$BACKUP_DIR/app_${STAMP}.tar.gz" -C /opt/huance/app .
printf '%s\n' "$BACKUP_DIR/db_${STAMP}.dump" "$BACKUP_DIR/app_${STAMP}.tar.gz"
