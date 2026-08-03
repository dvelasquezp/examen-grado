#!/bin/sh
set -e

normalize_db_url() {
  printf '%s' "$1" \
    | sed 's/&channel_binding=require//g' \
    | sed 's/?channel_binding=require&/?/g' \
    | sed 's/?channel_binding=require//g'
}

if [ -z "${DATABASE_URL:-}" ] || [ -z "${DATABASE_URL_SYNC:-}" ]; then
  echo "ERROR: configura DATABASE_URL y DATABASE_URL_SYNC en Render (examen-api → Environment)."
  exit 1
fi

export DATABASE_URL="$(normalize_db_url "$DATABASE_URL")"
export DATABASE_URL_SYNC="$(normalize_db_url "$DATABASE_URL_SYNC")"

echo ">> DATABASE_URL_SYNC host: $(printf '%s' "$DATABASE_URL_SYNC" | sed 's/.*@//; s/\/.*//')"

echo ">> Migraciones Alembic..."
if ! alembic upgrade head; then
  echo "ERROR: Alembic falló. Revisa DATABASE_URL_SYNC (Neon, conexión directa, ?sslmode=require)."
  exit 1
fi

echo ">> Iniciando API en 0.0.0.0:${PORT:-8000}..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
