"""Punto de entrada FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.infrastructure.persistence.neo4j.client import neo4j_client
from src.presentation.v1.catalog_router import router as catalog_router
from src.presentation.v1.concepts_router import router as concepts_router
from src.presentation.v1.ingestion_router import router as ingestion_router
from src.presentation.v1.search_router import router as search_router
from src.presentation.v1.sources_router import router as sources_router
from src.presentation.v1.study_router import router as study_router
from src.presentation.v1.system_router import router as system_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await neo4j_client.init_constraints()
    except Exception:
        pass
    yield
    await neo4j_client.close()


app = FastAPI(
    title=settings.app_name,
    description="Plataforma inteligente de preparación para el Examen de Grado Oral",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(concepts_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(study_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
