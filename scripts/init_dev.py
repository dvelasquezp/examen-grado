#!/usr/bin/env python3
"""Inicializa el entorno de desarrollo."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    print("=" * 60)
    print("Examen de Grado — Inicialización M1")
    print("=" * 60)

    env_file = ROOT / ".env"
    env_example = ROOT / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("✓ .env creado desde .env.example")

    local_env = ROOT / "apps" / "api" / ".env"
    if not local_env.exists() and env_file.exists():
        shutil.copy(env_file, local_env)
        print("✓ .env copiado a apps/api/")

    api_env = local_env if local_env.exists() else env_file
    if api_env.exists():
        content = api_env.read_text()
        if "CONTENT_PATH=." not in content and "CONTENT_PATH=/app/content" in content:
            local_content = content.replace(
                "CONTENT_PATH=/app/content",
                f"CONTENT_PATH={ROOT}",
            ).replace(
                "DATABASE_URL=postgresql+asyncpg://examen:examen@postgres:5432/examen_grado",
                "DATABASE_URL=postgresql+asyncpg://examen:examen@localhost:5432/examen_grado",
            ).replace(
                "DATABASE_URL_SYNC=postgresql://examen:examen@postgres:5432/examen_grado",
                "DATABASE_URL_SYNC=postgresql://examen:examen@localhost:5432/examen_grado",
            ).replace(
                "NEO4J_URI=bolt://neo4j:7687",
                "NEO4J_URI=bolt://localhost:7687",
            ).replace(
                "REDIS_URL=redis://redis:6379/0",
                "REDIS_URL=redis://localhost:6379/0",
            )
            api_env.write_text(local_content)
            print(f"✓ CONTENT_PATH configurado a {ROOT}")

    print("\nPara continuar:")
    print("  1. docker compose up -d postgres neo4j redis minio")
    print("  2. cd apps/api && pip install -e '.[dev]' && alembic upgrade head")
    print("  3. uvicorn src.main:app --reload --port 8000")
    print("  4. cd apps/web && npm install && npm run dev")
    print("=" * 60)


if __name__ == "__main__":
    main()
