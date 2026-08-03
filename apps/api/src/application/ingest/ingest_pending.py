"""Caso de uso: ingerir todos los documentos pendientes."""

from dataclasses import dataclass
from uuid import UUID

from src.application.ingest.ingest_document import IngestDocumentResult, IngestDocumentUseCase
from src.config.settings import Settings
from src.infrastructure.persistence.postgres.ingestion_repository import IngestionRepository


@dataclass
class IngestPendingResult:
    total: int
    completed: int
    failed: int
    skipped: int
    results: list[IngestDocumentResult]


class IngestPendingUseCase:
    def __init__(self, settings: Settings, repository: IngestionRepository):
        self.settings = settings
        self.repository = repository

    def execute(self, force: bool = False) -> IngestPendingResult:
        documents = self.repository.list_pending_documents()
        if force:
            from sqlalchemy import select

            from src.infrastructure.persistence.postgres.models import DocumentModel

            all_docs = self.repository.session.execute(select(DocumentModel)).scalars().all()
            documents = list(all_docs)

        ingest_use_case = IngestDocumentUseCase(self.settings, self.repository)
        results: list[IngestDocumentResult] = []
        completed = failed = skipped = 0

        for doc in documents:
            result = ingest_use_case.execute(doc.id, force=force)
            results.append(result)
            if result.skipped:
                skipped += 1
            elif result.status == "completed":
                completed += 1
            else:
                failed += 1

        return IngestPendingResult(
            total=len(documents),
            completed=completed,
            failed=failed,
            skipped=skipped,
            results=results,
        )
