#!/usr/bin/env bash
set -euo pipefail

DB="${POSTGRES_DB:-mota_poc}"

for f in /app/db/init/*.sql; do
  echo "Applying $f"
  gosu postgres psql -d "$DB" -v ON_ERROR_STOP=1 -f "$f"
done

gosu postgres psql -d "$DB" -v ON_ERROR_STOP=1 <<SQL
GRANT USAGE ON SCHEMA admin, core, gis, analytics, forecast, simulation, mart TO ${POSTGRES_USER};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA admin, core, gis, analytics, forecast, simulation, mart TO ${POSTGRES_USER};
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA admin, core, gis, analytics, forecast, simulation, mart TO ${POSTGRES_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA admin, core, gis, analytics, forecast, simulation, mart
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${POSTGRES_USER};
SQL
