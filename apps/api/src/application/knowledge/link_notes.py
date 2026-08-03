"""Caso de uso: vincular Apuntes a conceptos existentes."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.catalog.enums import DocumentType, SourceRole
from src.domain.knowledge.chunk_link import ConceptChunkLink
from src.domain.knowledge.concept import Concept
from src.infrastructure.knowledge.notes_linker import LinkCandidate, NotesConceptLinker
from src.infrastructure.persistence.neo4j.concept_sync import ConceptGraphSync
from src.infrastructure.persistence.postgres.concept_repository import ConceptRepository
from src.infrastructure.persistence.postgres.models import DocumentChunkModel, DocumentModel, SubjectModel
from src.infrastructure.persistence.postgres.knowledge_models import ConceptModel


@dataclass
class LinkNotesResult:
    subject_slug: str
    concepts_total: int
    chunks_scanned: int
    links_found: int
    links_created: int
    links_skipped: int


class LinkNotesUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.linker = NotesConceptLinker()
        self.concept_repo = ConceptRepository(session)
        self.graph_sync = ConceptGraphSync()

    async def execute(self, subject_slug: str) -> LinkNotesResult:
        subject = await self._get_subject(subject_slug)
        if not subject:
            raise ValueError(f"Materia no encontrada: {subject_slug}")

        concepts = await self._get_concepts(subject.id)
        if not concepts:
            raise ValueError(
                "No hay conceptos canónicos. Extrae primero desde Flashcards."
            )

        note_chunks = await self._get_notes_chunks(subject.id)
        chunk_inputs = [
            (chunk.content, chunk.id, document.id, document.filename, chunk.page_start)
            for chunk, document in note_chunks
        ]

        candidates = self.linker.find_links(concepts, chunk_inputs)
        links_created = 0
        links_skipped = 0

        for candidate in candidates:
            provenance = NotesConceptLinker.candidate_to_provenance(candidate)
            link = ConceptChunkLink(
                id=None,
                concept_id=candidate.concept_id,
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                page_number=candidate.page_number,
                match_type=candidate.match_type,
                relevance_score=candidate.relevance_score,
                excerpt=candidate.excerpt,
                provenance=provenance,
            )
            created = await self.concept_repo.upsert_chunk_link(link)
            if created:
                links_created += 1
                await self.graph_sync.link_chunk_mention(
                    concept_id=candidate.concept_id,
                    chunk_id=candidate.chunk_id,
                    document_filename=candidate.document_filename,
                    relevance=candidate.relevance_score,
                )
            else:
                links_skipped += 1

        return LinkNotesResult(
            subject_slug=subject_slug,
            concepts_total=len(concepts),
            chunks_scanned=len(note_chunks),
            links_found=len(candidates),
            links_created=links_created,
            links_skipped=links_skipped,
        )

    async def _get_subject(self, slug: str) -> SubjectModel | None:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _get_concepts(self, subject_id: UUID) -> list[Concept]:
        result = await self.session.execute(
            select(ConceptModel).where(ConceptModel.subject_id == subject_id)
        )
        return [
            Concept(
                id=m.id,
                subject_id=m.subject_id,
                slug=m.slug,
                title=m.title,
                definition=m.definition,
                confidence_score=m.confidence_score or 0.0,
            )
            for m in result.scalars().all()
        ]

    async def _get_notes_chunks(
        self, subject_id: UUID
    ) -> list[tuple[DocumentChunkModel, DocumentModel]]:
        result = await self.session.execute(
            select(DocumentChunkModel, DocumentModel)
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            .where(
                DocumentModel.subject_id == subject_id,
                DocumentModel.source_role == SourceRole.DOCTRINE,
                DocumentModel.document_type == DocumentType.LECTURE_NOTES,
            )
        )
        return list(result.all())
