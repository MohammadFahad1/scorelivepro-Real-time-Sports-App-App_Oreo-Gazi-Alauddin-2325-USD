#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Wait for the DB to be ready
if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Only run migrations if explicit environment variable is set
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Applying database migrations..."
    python manage.py migrate
fi

exec "$@"