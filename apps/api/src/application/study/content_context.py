"""Recupera fragmentos doctrinales para anclar prompts de Qwen."""

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.knowledge_models import (
    ConceptChunkLinkModel,
    ConceptModel,
)
from src.infrastructure.persistence.postgres.models import DocumentChunkModel, DocumentModel


class ContentContextService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_concept(self, concept: ConceptModel, *, max_chars: int = 3500) -> str:
        parts: list[str] = []
        if concept.definition:
            parts.append(f"Definición canónica de «{concept.title}»:\n{concept.definition}")

        linked = await self.session.execute(
            select(ConceptChunkLinkModel, DocumentChunkModel, DocumentModel)
            .join(DocumentChunkModel, DocumentChunkModel.id == ConceptChunkLinkModel.chunk_id)
            .join(DocumentModel, DocumentModel.id == ConceptChunkLinkModel.document_id)
            .where(ConceptChunkLinkModel.concept_id == concept.id)
            .order_by(ConceptChunkLinkModel.relevance_score.desc())
            .limit(6)
        )
        for _link, chunk, doc in linked.all():
            excerpt = (chunk.content_normalized or "")[:700]
            if excerpt:
                parts.append(f"[{doc.filename} p.{chunk.page_start or '?'}]\n{excerpt}")

        if len("\n\n".join(parts)) < 400:
            fts = await self._fts_chunks(concept.title, concept.subject_id, limit=4)
            parts.extend(fts)

        context = "\n\n---\n\n".join(parts)
        return context[:max_chars]

    async def _fts_chunks(
        self, query: str, subject_id: UUID, *, limit: int
    ) -> list[str]:
        sql = text("""
            SELECT dc.content_normalized, dc.page_start, d.filename
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.fts_vector @@ plainto_tsquery('spanish', :q)
              AND d.source_role = 'DOCTRINE'
              AND d.subject_id = :subject_id
            ORDER BY ts_rank_cd(dc.fts_vector, plainto_tsquery('spanish', :q)) DESC
            LIMIT :limit
        """)
        result = await self.session.execute(
            sql, {"q": query, "subject_id": str(subject_id), "limit": limit}
        )
        out: list[str] = []
        for row in result:
            excerpt = (row.content_normalized or "")[:700]
            if excerpt:
                out.append(f"[{row.filename} p.{row.page_start or '?'}]\n{excerpt}")
        return out
