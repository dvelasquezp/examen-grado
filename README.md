# Examen de Grado

Plataforma inteligente de aprendizaje jurídico para preparar el Examen de Grado Oral de la Universidad de Chile.

## Estado del proyecto

| Milestone | Estado |
|-----------|--------|
| M1 — Infraestructura | Completado |
| M2 — Ingesta MVP | Completado |
| M3 — Extracción de conceptos | En progreso |

## Requisitos

- Docker & Docker Compose
- Node.js 20+ (desarrollo frontend local)
- Python 3.12+ (desarrollo backend local)

## Inicio rápido

```bash
# 1. Configurar entorno
cp .env.example .env

# 2. Levantar servicios de infraestructura
docker compose up -d postgres neo4j redis minio

# 3. Backend (desarrollo local)
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# 4. Frontend (desarrollo local)
cd apps/web
npm install
npm run dev
```

## Estructura

```
Exámen de Grado/
├── Cedulario Examen de Grado.pdf    # Fuente de verdad (doctrina)
├── Derecho Civil/                   # Materia (auto-detectada)
│   ├── Flashcards-*.pdf
│   ├── Guía Examen de Grado - *.docx
│   └── Apuntes/*.pdf
├── apps/
│   ├── api/                         # FastAPI backend
│   └── web/                         # Next.js frontend
├── scripts/                         # Utilidades (descarga modelos, etc.)
└── docker-compose.yml
```

## Materias

Las materias se detectan automáticamente: cada carpeta en la raíz del proyecto (excepto carpetas de código) es una materia. Para agregar Derecho Penal, simplemente crea la carpeta `Derecho Penal/` con la estructura estándar.

## API

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Licencia

Uso privado — material académico personal.
