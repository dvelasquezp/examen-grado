#!/usr/bin/env bash
# Preparación local: descubrir + ingestar materiales (incl. DERECHO CIVIL 2).
# No toca producción. Requiere API local en :8000 y HF_TOKEN en .env para Qwen.
set -euo pipefail

API="${API_BASE:-http://localhost:8000/api/v1}"

echo "→ Descubriendo materias y documentos…"
curl -s -X POST "$API/catalog/discover" | python3 -m json.tool

echo "→ Ingestando documentos pendientes (puede tardar)…"
curl -s -X POST "$API/ingestion/ingest-pending?background=false" | python3 -m json.tool

echo
echo "Listo. Con HF_TOKEN en .env puedes:"
echo "  • Simulacro oral → evaluación Qwen/Qwen3-32B (fallback heurístico si HF falla)"
echo "  • curl -X POST $API/subjects/derecho-civil/concepts/<ID>/examples/generate"
echo "  • curl -X POST $API/subjects/derecho-civil/examples/generate -H 'Content-Type: application/json' -d '{\"limit\":5}'"
