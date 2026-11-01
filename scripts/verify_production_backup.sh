#!/usr/bin/env bash
set -euo pipefail

# Non-destructive backup verification. It never overwrites a live database.
# Usage: ./scripts/verify_production_backup.sh /path/to/app_backup.tar.gz /path/to/db_backup.dump

APP_BACKUP="${1:?app backup tar.gz is required}"
DB_BACKUP="${2:?postgres custom dump is required}"

test -r "$APP_BACKUP"
test -r "$DB_BACKUP"
tar -tzf "$APP_BACKUP" >/dev/null
pg_restore --list "$DB_BACKUP" >/dev/null
printf 'backup archive: valid\npostgres dump: valid\n'
