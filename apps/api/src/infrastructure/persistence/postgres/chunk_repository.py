"""Repositorio de chunks de documentos."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.knowledge_models import ConceptChunkLinkModel
from src.infrastructure.persistence.postgres.models import DocumentChunkModel, DocumentModel


class ChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_chunk_detail(
        self,
        chunk_id: UUID,
        *,
        concept_id: UUID | None = None,
    ) -> dict | None:
        result = await self.session.execute(
            select(DocumentChunkModel, DocumentModel)
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            .where(DocumentChunkModel.id == chunk_id)
        )
        row = result.one_or_none()
        if not row:
            return None

        chunk, document = row
        link = None
        if concept_id:
            link_result = await self.session.execute(
                select(ConceptChunkLinkModel).where(
                    ConceptChunkLinkModel.chunk_id == chunk_id,
                    ConceptChunkLinkModel.concept_id == concept_id,
                )
            )
            link = link_result.scalar_one_or_none()

        return {
            "chunk_id": chunk.id,
            "content": chunk.content,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "chapter": chunk.chapter,
            "section": chunk.section,
            "heading_path": chunk.heading_path,
            "chunk_type": chunk.chunk_type,
            "document_id": document.id,
            "document_filename": document.filename,
            "document_filepath": document.filepath,
            "document_type": document.document_type.value,
            "page_count": document.page_count,
            "excerpt": link.excerpt if link else None,
            "relevance_score": link.relevance_score if link else None,
            "match_type": link.match_type if link else None,
        }
