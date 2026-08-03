#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Instala Docker Desktop desde https://www.docker.com/products/docker-desktop/"
  exit 1
fi

echo "Construyendo e iniciando (primera vez puede tardar 10-15 min)..."
docker compose -f docker-compose.review.yml up --build -d

echo ""
echo "============================================"
echo "  App de revisión: http://localhost:3000"
echo "  API (docs):      http://localhost:8000/docs"
echo "============================================"
echo ""
echo "Para detener: docker compose -f docker-compose.review.yml down"
