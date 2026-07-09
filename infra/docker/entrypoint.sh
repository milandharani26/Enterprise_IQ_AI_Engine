#!/bin/bash
set -e

echo "Starting All-in-One Container Initialization..."

# 1. Ensure PostgreSQL directories have correct permissions
chown -R postgres:postgres /var/lib/postgresql /etc/postgresql /var/run/postgresql

# 2. Detect PostgreSQL version dynamically
PG_VERSION=$(ls /etc/postgresql/ | head -n 1)
if [ -z "$PG_VERSION" ]; then
    PG_VERSION="16"
fi
echo "Detected PostgreSQL version: $PG_VERSION"

# Check if database cluster exists. If not, initialize it.
if [ ! -d "/var/lib/postgresql/$PG_VERSION/main" ] || [ ! -f "/var/lib/postgresql/$PG_VERSION/main/PG_VERSION" ]; then
    echo "Initializing new PostgreSQL database cluster..."
    pg_createcluster $PG_VERSION main
    PG_VERSION=$(ls /etc/postgresql/ | head -n 1)
fi

# 3. Configure PostgreSQL to listen on port 5433
echo "Configuring PostgreSQL to listen on port 5433..."
sed -i "s/#port = 5432/port = 5433/g" /etc/postgresql/$PG_VERSION/main/postgresql.conf
sed -i "s/port = 5432/port = 5433/g" /etc/postgresql/$PG_VERSION/main/postgresql.conf

# Configure PostgreSQL pg_hba.conf to trust local logins inside the container
echo "local all all trust" > /etc/postgresql/$PG_VERSION/main/pg_hba.conf
echo "host all all 127.0.0.1/32 trust" >> /etc/postgresql/$PG_VERSION/main/pg_hba.conf

# 4. Start PostgreSQL temporarily for initialization & migration
echo "Starting PostgreSQL temporarily..."
pg_ctlcluster $PG_VERSION main start

# Wait for PostgreSQL to be ready
until pg_isready -p 5433; do
  echo "Waiting for PostgreSQL on port 5433..."
  sleep 1
done

# 5. Create database user and database if they do not exist
echo "Setting up PostgreSQL database and credentials..."
# Create/Alter user postgres with password 'priyank@3220' (matching .env default)
psql -h localhost -p 5433 -U postgres -c "ALTER USER postgres WITH PASSWORD 'priyank@3220';" || true

# Create the enterpriseiq_aii database
psql -h localhost -p 5433 -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'enterpriseiq_aii'" | grep -q 1 || \
psql -h localhost -p 5433 -U postgres -c "CREATE DATABASE enterpriseiq_aii;"

# Enable vector extension
psql -h localhost -p 5433 -U postgres -d enterpriseiq_aii -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 6. Run database migrations
echo "Running database migrations via Alembic..."
poetry run alembic upgrade head

# 7. Stop temporary PostgreSQL
echo "Stopping temporary PostgreSQL..."
pg_ctlcluster $PG_VERSION main stop

# 8. Configure supervisord with the correct PostgreSQL version
sed -i "s/<PG_VERSION>/$PG_VERSION/g" /etc/supervisor/supervisord.conf

# 9. Start supervisor to manage postgres, redis, celery, and fastapi
echo "Starting Supervisord..."
exec supervisord -c /etc/supervisor/supervisord.conf
