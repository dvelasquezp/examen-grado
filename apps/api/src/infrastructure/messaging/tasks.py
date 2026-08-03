"""Tareas Celery."""

from src.application.ingest.ingestion_service import ingest_document_sync, ingest_pending_sync
from src.infrastructure.messaging.celery_app import celery_app


@celery_app.task(name="src.infrastructure.messaging.tasks.discover_subjects")
def discover_subjects_task():
    return {"status": "queued", "message": "Descubrimiento programado"}


@celery_app.task(name="src.infrastructure.messaging.tasks.ingest_document")
def ingest_document_task(document_id: str, force: bool = False):
    from uuid import UUID

    result = ingest_document_sync(document_id=UUID(document_id), force=force)
    return {
        "status": result.status,
        "document_id": str(result.document_id),
        "chunks_created": result.chunks_created,
        "embeddings_created": result.embeddings_created,
        "error": result.error,
    }


@celery_app.task(name="src.infrastructure.messaging.tasks.ingest_pending")
def ingest_pending_task(force: bool = False):
    result = ingest_pending_sync(force=force)
    return {
        "total": result.total,
        "completed": result.completed,
        "failed": result.failed,
        "skipped": result.skipped,
    }
