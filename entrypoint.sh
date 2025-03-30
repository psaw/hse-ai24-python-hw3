#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Database connection variables (should be passed from Docker environment)
DB_HOST="${DB_HOST:-db}" # Default to 'db' service name if not set
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER}"
DB_PASS="${DB_PASS}"
DB_NAME="${DB_NAME}"

echo "Entrypoint script started..."

# --- Wait for PostgreSQL ---
echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

# Use pg_isready to check if the database is accepting connections.
# Requires postgresql-client to be installed in the Docker image.
# Loop until pg_isready returns success (exit code 0)
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q -d "$DB_NAME"; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - executing command"

# --- Run Alembic Migrations ---
echo "Running database migrations..."
# Alembic should be configured to read DB connection info from environment variables
# or alembic.ini which interpolates environment variables.
alembic upgrade head

echo "Database migrations finished."

# --- Execute the main container command ---
# This will run the CMD specified in the Dockerfile or the command specified in docker-compose.yml
echo "Executing main command: $@"
exec "$@" 