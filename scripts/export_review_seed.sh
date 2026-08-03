#!/usr/bin/env bash
# Exporta la base local (con conceptos ya cargados) para incluirla en el paquete de revisión.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/data/review-seed.sql"
mkdir -p "$ROOT/data"

echo "Exportando base de datos a $OUT ..."
docker compose exec -T postgres pg_dump -U examen --no-owner --no-acl examen_grado > "$OUT"

LINES=$(wc -l < "$OUT" | tr -d ' ')
if [ "$LINES" -lt 50 ]; then
  echo "ADVERTENCIA: el dump parece muy pequeño ($LINES líneas)."
  echo "¿Corriste discover, ingest, extract y link-notes antes?"
fi
echo "Listo. Incluye data/review-seed.sql al empaquetar."
