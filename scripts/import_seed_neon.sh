#!/usr/bin/env bash
# Importa review-seed.sql a Neon (u otro Postgres con pgvector).
# Uso:
#   export NEON_DATABASE_URL='postgresql://user:pass@host/neondb?sslmode=require'
#   ./scripts/import_seed_neon.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SEED="$ROOT/data/review-seed.sql"
URL="${NEON_DATABASE_URL:-${DATABASE_URL_SYNC:-}}"

if [ -z "$URL" ]; then
  echo "ERROR: define NEON_DATABASE_URL o DATABASE_URL_SYNC"
  exit 1
fi

if [ ! -f "$SEED" ]; then
  echo "ERROR: no existe $SEED — corre ./scripts/export_review_seed.sh antes"
  exit 1
fi

# Quitar channel_binding (incompatible con algunos clientes)
URL="${URL//&channel_binding=require/}"
URL="${URL//?channel_binding=require&/?}"
URL="${URL//?channel_binding=require/}"

psql_cmd() {
  if command -v psql >/dev/null 2>&1; then
    psql "$URL" "$@"
  else
    docker run --rm -i postgres:16-alpine psql "$URL" "$@"
  fi
}

psql_file() {
  if command -v psql >/dev/null 2>&1; then
    psql "$URL" -f "$SEED"
  else
    docker run --rm \
      -v "$SEED:/seed.sql:ro" \
      postgres:16-alpine \
      psql "$URL" -f /seed.sql
  fi
}

echo ">> Habilitando pgvector..."
psql_cmd -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ">> Importando seed (~50 MB, puede tardar 1-2 min)..."
psql_file

echo ">> Listo."
psql_cmd -c "SELECT COUNT(*) AS conceptos FROM public.concepts;"
