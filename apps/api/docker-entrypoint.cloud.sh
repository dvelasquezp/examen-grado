#!/bin/sh
set -e

echo ">> Migraciones Alembic..."
alembic upgrade head

if [ "${RESTORE_SEED:-true}" = "true" ] && [ -f /seed/review-seed.sql ]; then
  COUNT=$(psql "$DATABASE_URL_SYNC" -tAc "SELECT COUNT(*) FROM concepts" 2>/dev/null || echo "0")
  COUNT=$(echo "$COUNT" | tr -d ' ')
  if [ "$COUNT" = "0" ] || [ -z "$COUNT" ]; then
    echo ">> Restaurando base de revisión (primera vez)..."
    psql "$DATABASE_URL_SYNC" -f /seed/review-seed.sql || echo "AVISO: seed parcial o ya aplicado"
  else
    echo ">> Base ya tiene datos ($COUNT conceptos); omitiendo seed."
  fi
fi

echo ">> Iniciando API..."
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
