#!/usr/bin/env bash
# Demo online para el experto — sin Render, sin Neon en la nube.
# Expone tu app local con un link público (ngrok).
#
# Requisitos: Docker Desktop + cuenta gratis en ngrok.com
#
# Uso:
#   ./scripts/demo-ngrok.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Instala Docker Desktop → https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if ! command -v ngrok >/dev/null 2>&1; then
  echo ""
  echo "ERROR: Falta ngrok."
  echo "  1. brew install ngrok"
  echo "  2. Crea cuenta en https://ngrok.com"
  echo "  3. ngrok config add-authtoken TU_TOKEN"
  echo "  4. Vuelve a ejecutar este script"
  exit 1
fi

echo ">> Levantando app (Docker, ~5 min la primera vez)..."
docker compose -f docker-compose.review.yml up --build -d

echo ">> Esperando que responda en localhost:3000..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:3000 >/dev/null 2>&1; then
    echo ">> App lista en http://localhost:3000"
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "ERROR: La app no arrancó. Revisa: docker compose -f docker-compose.review.yml logs"
    exit 1
  fi
  sleep 5
done

echo ""
echo "============================================"
echo "  Abriendo link público con ngrok..."
echo "  Copia la URL https://....ngrok-free.app"
echo "  y envíasela al experto."
echo ""
echo "  Mantén esta ventana abierta y tu Mac encendida."
echo "  Ctrl+C para cerrar el túnel (la app sigue en local)."
echo "============================================"
echo ""

ngrok http 3000
