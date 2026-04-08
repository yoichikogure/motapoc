#!/usr/bin/env bash
set -euo pipefail

export POSTGRES_DB="${POSTGRES_DB:-mota_poc}"
export POSTGRES_USER="${POSTGRES_USER:-poc}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-pocpass}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://poc:pocpass@127.0.0.1:5432/mota_poc}"

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
export PGDATA

find_pg_bin() {
  for base in /usr/lib/postgresql/*/bin; do
    if [ -x "$base/initdb" ] && [ -x "$base/pg_ctl" ] && [ -x "$base/postgres" ]; then
      echo "$base"
      return 0
    fi
  done
  return 1
}

PGBIN="$(find_pg_bin || true)"

if [ -z "$PGBIN" ]; then
  echo "ERROR: PostgreSQL server binaries not found."
  echo "Check installed files:"
  ls -R /usr/lib/postgresql 2>/dev/null || true
  echo "PATH lookup:"
  command -v initdb || true
  command -v pg_ctl || true
  command -v postgres || true
  exit 1
fi

echo "Using PostgreSQL binaries from: $PGBIN"
echo "Using PGDATA: $PGDATA"

mkdir -p "$PGDATA"
chown -R postgres:postgres /var/lib/postgresql

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Initializing PostgreSQL cluster..."
  gosu postgres "$PGBIN/initdb" -D "$PGDATA"
fi

echo "Starting PostgreSQL..."
gosu postgres "$PGBIN/pg_ctl" -D "$PGDATA" -o "-c listen_addresses='127.0.0.1'" -w start

if ! gosu postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'" | grep -q 1; then
  gosu postgres psql -c "CREATE ROLE ${POSTGRES_USER} LOGIN PASSWORD '${POSTGRES_PASSWORD}';"
fi

if ! gosu postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" | grep -q 1; then
  gosu postgres createdb -O "${POSTGRES_USER}" "${POSTGRES_DB}"
fi

/app/docker/init-db.sh

echo "Stopping temporary PostgreSQL..."
gosu postgres "$PGBIN/pg_ctl" -D "$PGDATA" -m fast stop

echo "Starting supervisord..."
exec /usr/bin/supervisord -c /app/docker/supervisord.conf