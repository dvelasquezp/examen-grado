"""Caso de uso: extraer conceptos desde chunks ingeridos."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.catalog.enums import DocumentType, SourceRole
from src.domain.knowledge.concept import Concept, ConceptDefinition
from src.infrastructure.ai.embedder import EmbeddingService
from src.infrastructure.knowledge.concept_merger import ConceptMerger
from src.infrastructure.knowledge.rule_extractor import (
    ExtractedConceptCandidate,
    RuleBasedConceptExtractor,
    candidate_to_provenance,
)
from src.infrastructure.persistence.neo4j.concept_sync import ConceptGraphSync
from src.infrastructure.persistence.postgres.catalog_repository import CatalogRepository
from src.infrastructure.persistence.postgres.concept_repository import ConceptRepository
from src.infrastructure.persistence.postgres.models import DocumentChunkModel, DocumentModel, SubjectModel
from src.infrastructure.persistence.postgres.knowledge_models import ConceptModel


@dataclass
class ExtractConceptsResult:
    subject_slug: str
    candidates_found: int
    concepts_created: int
    concepts_updated: int
    definitions_added: int


class ExtractConceptsUseCase:
    def __init__(self, session: AsyncSession, settings):
        self.session = session
        self.settings = settings
        self.extractor = RuleBasedConceptExtractor()
        self.merger = ConceptMerger()
        self.concept_repo = ConceptRepository(session)
        self.graph_sync = ConceptGraphSync()
        self.embedder = EmbeddingService(settings)

    async def execute(self, subject_slug: str) -> ExtractConceptsResult:
        subject = await self._get_subject(subject_slug)
        if not subject:
            raise ValueError(f"Materia no encontrada: {subject_slug}")

        chunks = await self._get_flashcard_chunks(subject.id)
        candidates: list[ExtractedConceptCandidate] = []

        for chunk, document in chunks:
            extracted = self.extractor.extract_from_chunk(
                chunk.content,
                document_id=document.id,
                document_filename=document.filename,
                document_type=document.document_type,
                source_role=document.source_role,
                chunk_id=chunk.id,
                page_start=chunk.page_start,
                chapter=chunk.chapter,
                section=chunk.section,
            )
            candidates.extend(extracted)

        existing_models = await self.session.execute(
            select(ConceptModel)
            .where(ConceptModel.subject_id == subject.id)
        )
        existing = [
            Concept(
                id=m.id,
                subject_id=m.subject_id,
                slug=m.slug,
                title=m.title,
                definition=m.definition,
                confidence_score=m.confidence_score or 0.0,
            )
            for m in existing_models.scalars().all()
        ]

        concepts_created = 0
        concepts_updated = 0
        definitions_added = 0

        for candidate in candidates:
            concept = self.merger.find_matching_concept(candidate.title, existing)
            is_new = concept is None

            if is_new:
                concept = Concept(
                    id=None,
                    subject_id=subject.id,
                    slug=Concept.slugify(candidate.title),
                    title=candidate.title,
                    definition=candidate.definition,
                    subtopic=candidate.subtopic,
                    confidence_score=candidate.confidence,
                )
                concept = await self.concept_repo.upsert_concept(concept)
                existing.append(concept)
                concepts_created += 1
            else:
                concepts_updated += 1
                if candidate.confidence > concept.confidence_score:
                    concept.confidence_score = candidate.confidence
                    if len(candidate.definition) > len(concept.definition or ""):
                        concept.definition = candidate.definition
                await self.concept_repo.upsert_concept(concept)

            is_primary = True
            provenance = candidate_to_provenance(candidate)
            definition = ConceptDefinition(
                text=candidate.definition,
                is_primary=is_primary,
                source_type="EXTRACTED",
                document_id=candidate.document_id,
                page_number=candidate.page_number,
                chunk_id=candidate.chunk_id,
                confidence=candidate.confidence,
                provenance=provenance,
                display_label=provenance["statements"][0]["display_label"],
            )
            await self.concept_repo.add_definition(concept.id, definition)  # type: ignore[arg-type]
            definitions_added += 1

            await self.graph_sync.upsert_concept(
                concept_id=concept.id,  # type: ignore[arg-type]
                title=concept.title,
                slug=concept.slug,
                subject_slug=subject_slug,
                subtopic=concept.subtopic,
                confidence=concept.confidence_score,
            )

            if self.embedder.enabled and concept.id:
                await self._embed_concept(concept)

        return ExtractConceptsResult(
            subject_slug=subject_slug,
            candidates_found=len(candidates),
            concepts_created=concepts_created,
            concepts_updated=concepts_updated,
            definitions_added=definitions_added,
        )

    async def _embed_concept(self, concept: Concept) -> None:
        from src.infrastructure.persistence.postgres.models import EmbeddingModel

        text = f"{concept.title}. {concept.definition or ''}"
        vector = self.embedder.embed_texts([text])[0]
        if all(v == 0.0 for v in vector):
            return

        existing = await self.session.execute(
            select(EmbeddingModel).where(
                EmbeddingModel.entity_type == "concept",
                EmbeddingModel.entity_id == concept.id,
                EmbeddingModel.model == self.embedder.model_name,
            )
        )
        model = existing.scalar_one_or_none()
        if model:
            model.vector = vector
        else:
            self.session.add(
                EmbeddingModel(
                    entity_type="concept",
                    entity_id=concept.id,
                    model=self.embedder.model_name,
                    dimensions=self.embedder.dimensions,
                    vector=vector,
                )
            )

    async def _get_subject(self, slug: str) -> SubjectModel | None:
        result = await self.session.execute(
            select(SubjectModel).where(SubjectModel.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _get_flashcard_chunks(
        self, subject_id: UUID
    ) -> list[tuple[DocumentChunkModel, DocumentModel]]:
        result = await self.session.execute(
            select(DocumentChunkModel, DocumentModel)
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            .where(
                DocumentModel.subject_id == subject_id,
                DocumentModel.source_role == SourceRole.DOCTRINE,
                DocumentModel.document_type == DocumentType.FLASHCARDS,
            )
        )
        return list(result.all())
