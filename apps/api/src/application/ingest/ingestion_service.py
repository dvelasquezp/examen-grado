"""Servicio de ingesta (sync, compartido por API y Celery)."""

from uuid import UUID

from sqlalchemy import select

from src.application.ingest.ingest_document import IngestDocumentResult, IngestDocumentUseCase
from src.application.ingest.ingest_pending import IngestPendingResult
from src.config.settings import get_settings
from src.infrastructure.persistence.postgres.ingestion_repository import IngestionRepository
from src.infrastructure.persistence.postgres.models import DocumentModel
from src.infrastructure.persistence.postgres.sync_database import SyncSessionLocal


def ingest_document_sync(document_id: UUID, force: bool = False) -> IngestDocumentResult:
    settings = get_settings()
    session = SyncSessionLocal()
    try:
        repo = IngestionRepository(session)
        use_case = IngestDocumentUseCase(settings, repo)
        result = use_case.execute(document_id, force=force)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ingest_pending_sync(force: bool = False) -> IngestPendingResult:
    settings = get_settings()
    session = SyncSessionLocal()
    try:
        repo = IngestionRepository(session)
        if force:
            documents = list(session.execute(select(DocumentModel)).scalars().all())
        else:
            documents = repo.list_pending_documents()
        document_ids = [doc.id for doc in documents]
    finally:
        session.close()

    results: list[IngestDocumentResult] = []
    completed = failed = skipped = 0

    for doc_id in document_ids:
        result = ingest_document_sync(doc_id, force=force)
        results.append(result)
        if result.skipped:
            skipped += 1
        elif result.status == "completed":
            completed += 1
        else:
            failed += 1

    return IngestPendingResult(
        total=len(document_ids),
        completed=completed,
        failed=failed,
        skipped=skipped,
        results=results,
    )
