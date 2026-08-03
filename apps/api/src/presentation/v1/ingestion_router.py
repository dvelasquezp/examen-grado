"""Router de ingesta de documentos."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ingest.ingestion_service import ingest_document_sync, ingest_pending_sync
from src.infrastructure.persistence.postgres.database import get_db_session
from src.infrastructure.persistence.postgres.models import DocumentModel, IngestionRunModel
from src.presentation.v1.ingestion_schemas import (
    IngestDocumentResponse,
    IngestPendingResponse,
    IngestionRunResponse,
)

router = APIRouter(prefix="/ingestion", tags=["Ingesta"])


def _to_response(result) -> IngestDocumentResponse:
    return IngestDocumentResponse(
        document_id=result.document_id,
        filename=result.filename,
        status=result.status,
        chunks_created=result.chunks_created,
        embeddings_created=result.embeddings_created,
        page_count=result.page_count,
        skipped=result.skipped,
        error=result.error,
    )


@router.post("/documents/{document_id}/ingest", response_model=IngestDocumentResponse)
async def ingest_document(
    document_id: UUID,
    force: bool = False,
    background: bool = False,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_db_session),
):
    doc = await session.get(DocumentModel, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if background:
        background_tasks.add_task(ingest_document_sync, document_id, force)
        return IngestDocumentResponse(
            document_id=document_id,
            filename=doc.filename,
            status="processing",
            chunks_created=0,
            embeddings_created=0,
            page_count=doc.page_count or 0,
        )

    result = ingest_document_sync(document_id, force=force)
    if result.error and result.status == "failed":
        raise HTTPException(status_code=500, detail=result.error)
    return _to_response(result)


@router.post("/ingest-pending", response_model=IngestPendingResponse)
async def ingest_pending(
    force: bool = False,
    background: bool = False,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    if background:
        background_tasks.add_task(ingest_pending_sync, force)
        return IngestPendingResponse(
            total=0,
            completed=0,
            failed=0,
            skipped=0,
            results=[],
        )

    result = ingest_pending_sync(force=force)
    return IngestPendingResponse(
        total=result.total,
        completed=result.completed,
        failed=result.failed,
        skipped=result.skipped,
        results=[_to_response(r) for r in result.results],
    )


@router.get("/documents/{document_id}/runs", response_model=list[IngestionRunResponse])
async def list_ingestion_runs(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(IngestionRunModel)
        .where(IngestionRunModel.document_id == document_id)
        .order_by(IngestionRunModel.started_at.desc())
    )
    runs = result.scalars().all()
    return [
        IngestionRunResponse(
            id=r.id,
            document_id=r.document_id,
            status=r.status,
            started_at=r.started_at.isoformat() if r.started_at else "",
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            stats=r.stats,
            errors=r.errors,
        )
        for r in runs
    ]
