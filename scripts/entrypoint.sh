#!/bin/sh
set -e

python scripts/wait_for_db.py

if [ "${RUN_DB_MIGRATIONS:-true}" = "true" ]; then
  echo "Running database migrations..."
  flask db upgrade
fi

echo "Starting application..."
exec "$@"
