"""Router de health check y sistema."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings, get_settings
from src.infrastructure.ai.model_router import ModelRouter, TaskType
from src.infrastructure.persistence.neo4j.client import neo4j_client
from src.infrastructure.persistence.postgres.database import get_db_session
from src.presentation.v1.schemas import HealthResponse, ModelInfoResponse

router = APIRouter(tags=["Sistema"])


@router.get("/healthz")
async def liveness_probe():
    """Probe simple para Render (sin dependencias externas)."""
    return {"status": "ok"}


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_db_session)):
    services: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        services["postgres"] = "ok"
    except Exception as e:
        services["postgres"] = f"error: {e}"

    try:
        neo4j_ok = await neo4j_client.verify_connectivity()
        services["neo4j"] = "ok" if neo4j_ok else "error"
    except Exception as e:
        services["neo4j"] = f"error: {e}"

    postgres_ok = services.get("postgres") == "ok"
    return HealthResponse(
        status="ok" if postgres_ok else "degraded",
        services=services,
    )


@router.get("/models", response_model=ModelInfoResponse)
async def list_models(settings: Settings = Depends(get_settings)):
    router_instance = ModelRouter(settings)
    return ModelInfoResponse(
        models=router_instance.list_models(),
        tasks=[t.value for t in TaskType],
    )
