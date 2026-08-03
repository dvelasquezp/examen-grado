"""Caso de uso: descubrir materias y documentos."""

from dataclasses import dataclass

from src.config.settings import Settings
from src.domain.catalog.discovery import SubjectDiscoveryService
from src.infrastructure.persistence.postgres.catalog_repository import CatalogRepository


@dataclass
class DiscoverSubjectsResult:
    subjects_found: int
    documents_found: int
    documents_new: int
    documents_updated: int
    scanned_paths: int
    skipped_paths: int


class DiscoverSubjectsUseCase:
    def __init__(self, settings: Settings, repository: CatalogRepository):
        self.discovery = SubjectDiscoveryService(settings)
        self.repository = repository

    async def execute(self) -> DiscoverSubjectsResult:
        result = self.discovery.discover()
        documents_new = 0
        documents_updated = 0

        subject_id_map: dict[str, object] = {}
        for subject in result.subjects:
            saved = await self.repository.upsert_subject(subject)
            subject_id_map[saved.slug] = saved.id

        existing_paths = {d.filepath for d in await self.repository.list_documents()}

        for discovered in result.documents:
            subject_id = None
            if discovered.subject:
                subject_id = subject_id_map.get(discovered.subject.slug)

            saved = await self.repository.upsert_document(discovered.document, subject_id)  # type: ignore[arg-type]
            if discovered.document.filepath in existing_paths:
                documents_updated += 1
            else:
                documents_new += 1

        return DiscoverSubjectsResult(
            subjects_found=len(result.subjects),
            documents_found=len(result.documents),
            documents_new=documents_new,
            documents_updated=documents_updated,
            scanned_paths=result.scanned_paths,
            skipped_paths=result.skipped_paths,
        )
