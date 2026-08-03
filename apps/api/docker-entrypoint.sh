#!/bin/sh
set -e

echo ">> Migraciones Alembic..."
alembic upgrade head

echo ">> Iniciando API..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
