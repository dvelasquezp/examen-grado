"""Repositorio de conceptos."""

from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.knowledge.concept import Concept, ConceptDefinition
from src.domain.knowledge.chunk_link import ConceptChunkLink
from src.infrastructure.persistence.postgres.knowledge_models import (
    ConceptChunkLinkModel,
    ConceptDefinitionModel,
    ConceptModel,
)


class ConceptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, concept_id: UUID) -> Concept | None:
        result = await self.session.execute(
            select(ConceptModel)
            .options(selectinload(ConceptModel.definitions))
            .where(ConceptModel.id == concept_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_slug(self, subject_id: UUID, slug: str) -> Concept | None:
        result = await self.session.execute(
            select(ConceptModel)
            .options(selectinload(ConceptModel.definitions))
            .where(ConceptModel.subject_id == subject_id, ConceptModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_by_subject(
        self,
        subject_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        q: str | None = None,
    ) -> list[Concept]:
        query = (
            select(ConceptModel)
            .options(selectinload(ConceptModel.definitions))
            .where(ConceptModel.subject_id == subject_id)
            .order_by(ConceptModel.title)
            .limit(limit)
            .offset(offset)
        )
        if q:
            query = query.where(
                or_(
                    ConceptModel.title.ilike(f"%{q}%"),
                    ConceptModel.definition.ilike(f"%{q}%"),
                )
            )
        result = await self.session.execute(query)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def count_by_subject(self, subject_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(ConceptModel.id)).where(ConceptModel.subject_id == subject_id)
        )
        return result.scalar() or 0

    async def upsert_concept(self, concept: Concept) -> Concept:
        existing = await self.session.execute(
            select(ConceptModel).where(
                ConceptModel.subject_id == concept.subject_id,
                ConceptModel.slug == concept.slug,
            )
        )
        model = existing.scalar_one_or_none()

        if model:
            model.title = concept.title
            if concept.subtopic:
                model.subtopic = concept.subtopic
            model.confidence_score = max(model.confidence_score, concept.confidence_score)
            if concept.definition and (
                not model.definition or concept.confidence_score >= model.confidence_score
            ):
                model.definition = concept.definition
        else:
            model = ConceptModel(
                subject_id=concept.subject_id,
                slug=concept.slug,
                title=concept.title,
                definition=concept.definition,
                subtopic=concept.subtopic,
                difficulty=concept.difficulty,
                importance_score=concept.importance_score,
                confidence_score=concept.confidence_score,
                metadata_=concept.metadata,
            )
            self.session.add(model)

        await self.session.flush()
        concept.id = model.id
        return concept

    async def add_definition(
        self,
        concept_id: UUID,
        definition: ConceptDefinition,
    ) -> ConceptDefinitionModel:
        existing = await self.session.execute(
            select(ConceptDefinitionModel).where(
                ConceptDefinitionModel.concept_id == concept_id,
                ConceptDefinitionModel.chunk_id == definition.chunk_id,
                ConceptDefinitionModel.text == definition.text,
            )
        )
        found = existing.scalar_one_or_none()
        if found:
            return found

        model = ConceptDefinitionModel(
            concept_id=concept_id,
            text=definition.text,
            is_primary=definition.is_primary,
            source_type=definition.source_type,
            document_id=definition.document_id,
            page_number=definition.page_number,
            chunk_id=definition.chunk_id,
            confidence=definition.confidence,
            provenance=definition.provenance,
        )
        self.session.add(model)
        await self.session.flush()

        if definition.is_primary:
            concept_result = await self.session.execute(
                select(ConceptModel).where(ConceptModel.id == concept_id)
            )
            concept_model = concept_result.scalar_one()
            concept_model.definition = definition.text

        return model

    async def upsert_chunk_link(self, link: ConceptChunkLink) -> bool:
        """Inserta vínculo si no existe. Retorna True si se creó."""
        existing = await self.session.execute(
            select(ConceptChunkLinkModel).where(
                ConceptChunkLinkModel.concept_id == link.concept_id,
                ConceptChunkLinkModel.chunk_id == link.chunk_id,
            )
        )
        if existing.scalar_one_or_none():
            return False

        model = ConceptChunkLinkModel(
            concept_id=link.concept_id,
            chunk_id=link.chunk_id,
            document_id=link.document_id,
            page_number=link.page_number,
            match_type=link.match_type,
            relevance_score=link.relevance_score,
            excerpt=link.excerpt,
            provenance=link.provenance,
        )
        self.session.add(model)
        await self.session.flush()
        link.id = model.id
        return True

    async def list_chunk_links(self, concept_id: UUID) -> list[ConceptChunkLink]:
        from src.infrastructure.persistence.postgres.models import DocumentChunkModel, DocumentModel

        result = await self.session.execute(
            select(ConceptChunkLinkModel, DocumentModel, DocumentChunkModel)
            .join(DocumentModel, ConceptChunkLinkModel.document_id == DocumentModel.id)
            .join(DocumentChunkModel, ConceptChunkLinkModel.chunk_id == DocumentChunkModel.id)
            .where(ConceptChunkLinkModel.concept_id == concept_id)
            .order_by(ConceptChunkLinkModel.relevance_score.desc())
        )
        links: list[ConceptChunkLink] = []
        for link_model, doc_model, chunk_model in result.all():
            links.append(
                ConceptChunkLink(
                    id=link_model.id,
                    concept_id=link_model.concept_id,
                    chunk_id=link_model.chunk_id,
                    document_id=link_model.document_id,
                    page_number=link_model.page_number,
                    match_type=link_model.match_type,
                    relevance_score=link_model.relevance_score or 0.0,
                    excerpt=link_model.excerpt,
                    provenance=link_model.provenance or {},
                    document_filename=doc_model.filename,
                    chunk_content=chunk_model.content,
                    created_at=link_model.created_at,
                )
            )
        return links

    async def count_chunk_links_by_subject(self, subject_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(ConceptChunkLinkModel.id))
            .join(ConceptModel, ConceptChunkLinkModel.concept_id == ConceptModel.id)
            .where(ConceptModel.subject_id == subject_id)
        )
        return result.scalar() or 0

    async def search_fts(self, query: str, subject_id: UUID | None, limit: int = 20) -> list[dict]:
        sql = text("""
            SELECT c.id, c.title, c.slug, c.definition, c.subtopic,
                   ts_rank_cd(c_fts.fts, plainto_tsquery('spanish', :q)) AS rank
            FROM concepts c
            JOIN (
                SELECT concept_id,
                       to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(definition,'')) AS fts
                FROM concepts
            ) c_fts ON c_fts.concept_id = c.id
            WHERE c_fts.fts @@ plainto_tsquery('spanish', :q)
            AND (:subject_id::uuid IS NULL OR c.subject_id = :subject_id)
            ORDER BY rank DESC
            LIMIT :limit
        """)
        result = await self.session.execute(
            sql,
            {"q": query, "subject_id": str(subject_id) if subject_id else None, "limit": limit},
        )
        return [
            {
                "id": str(row.id),
                "title": row.title,
                "slug": row.slug,
                "definition": row.definition,
                "subtopic": row.subtopic,
                "score": float(row.rank),
                "match_type": "keyword",
            }
            for row in result
        ]

    def _to_domain(self, model: ConceptModel) -> Concept:
        return Concept(
            id=model.id,
            subject_id=model.subject_id,
            slug=model.slug,
            title=model.title,
            definition=model.definition,
            simple_explanation=model.simple_explanation,
            subtopic=model.subtopic,
            difficulty=model.difficulty or 3,
            importance_score=model.importance_score or 0.5,
            confidence_score=model.confidence_score or 0.0,
            definitions=[
                ConceptDefinition(
                    text=d.text,
                    is_primary=d.is_primary,
                    source_type=d.source_type,
                    document_id=d.document_id,
                    page_number=d.page_number,
                    chunk_id=d.chunk_id,
                    confidence=d.confidence or 0.0,
                    provenance=d.provenance or {},
                    display_label=(d.provenance or {}).get("statements", [{}])[0].get(
                        "display_label", ""
                    )
                    if d.provenance
                    else "",
                )
                for d in model.definitions
            ],
            neo4j_node_id=model.neo4j_node_id,
            metadata=model.metadata_ or {},
            created_at=model.created_at,
        )
