#!/usr/bin/env bash
# Crea dist/examen-grado-revision.zip listo para enviar al experto.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist/examen-grado-revision"
ZIP="$ROOT/dist/examen-grado-revision.zip"

echo "== Generando checklist Excel =="
cd "$ROOT/apps/api"
if [ -d .venv ]; then source .venv/bin/activate; fi
pip install -q openpyxl 2>/dev/null || pip install openpyxl
python "$ROOT/scripts/generate_checklist_excel.py" "$ROOT/dist/checklist-revision-experto.xlsx"

echo "== Preparando carpeta de entrega =="
rm -rf "$DIST"
mkdir -p "$DIST/data"

# Código mínimo para Docker
rsync -a \
  --exclude '.next' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.git' \
  "$ROOT/apps" "$DIST/"
cp "$ROOT/docker-compose.review.yml" "$DIST/"
cp "$ROOT/.env.review" "$DIST/.env.review"

# Materiales jurídicos (ajusta si tus carpetas tienen otro nombre)
for item in "Derecho Civil" "Cedulario Examen de Grado.pdf"; do
  if [ -e "$ROOT/$item" ]; then
    cp -R "$ROOT/$item" "$DIST/"
  fi
done

# Base precargada (opcional pero recomendado)
if [ -f "$ROOT/data/review-seed.sql" ]; then
  cp "$ROOT/data/review-seed.sql" "$DIST/data/review-seed.sql"
fi

# Scripts de arranque y documentación
cp "$ROOT/scripts/review_up.sh" "$DIST/iniciar-revision.sh"
cp "$ROOT/scripts/review_up.bat" "$DIST/Iniciar-Revision.bat"
cp "$ROOT/dist/checklist-revision-experto.xlsx" "$DIST/"
cp "$ROOT/docs/LEEME-REVISION.txt" "$DIST/LEEME.txt"

chmod +x "$DIST/iniciar-revision.sh"

echo "== Comprimiendo =="
rm -f "$ZIP"
(cd "$ROOT/dist" && zip -rq examen-grado-revision.zip examen-grado-revision)

echo ""
echo "Paquete listo: $ZIP"
echo "Envía el .zip + checklist Excel (también va dentro del zip)."
du -h "$ZIP"
