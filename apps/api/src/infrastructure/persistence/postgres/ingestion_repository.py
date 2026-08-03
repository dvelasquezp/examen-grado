"""Repositorio de ingesta (chunks, runs, embeddings)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from src.domain.catalog.enums import IngestionStatus
from src.domain.ingestion.chunk import DocumentChunk
from src.infrastructure.persistence.postgres.models import (
    DocumentChunkModel,
    DocumentModel,
    EmbeddingModel,
    IngestionRunModel,
)
from src.infrastructure.persistence.postgres.knowledge_models import (
    ConceptChunkLinkModel,
    ConceptDefinitionModel,
)


class IngestionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_document(self, document_id: UUID) -> DocumentModel | None:
        return self.session.get(DocumentModel, document_id)

    def list_pending_documents(self) -> list[DocumentModel]:
        result = self.session.execute(
            select(DocumentModel).where(
                DocumentModel.ingestion_status.in_([
                    IngestionStatus.PENDING,
                    IngestionStatus.FAILED,
                ])
            )
        )
        return list(result.scalars().all())

    def create_ingestion_run(self, document_id: UUID) -> IngestionRunModel:
        run = IngestionRunModel(
            document_id=document_id,
            status=IngestionStatus.PROCESSING,
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.flush()
        return run

    def complete_ingestion_run(
        self,
        run: IngestionRunModel,
        status: str,
        stats: dict | None = None,
        errors: dict | None = None,
    ) -> None:
        run.status = status
        run.completed_at = datetime.now(UTC)
        run.stats = stats
        run.errors = errors

    def set_document_status(
        self,
        document: DocumentModel,
        status: IngestionStatus,
        page_count: int | None = None,
    ) -> None:
        document.ingestion_status = status
        if status == IngestionStatus.COMPLETED:
            document.last_ingested_at = datetime.now(UTC)
        if page_count is not None:
            document.page_count = page_count

    def delete_document_chunks(self, document_id: UUID) -> int:
        chunk_ids = list(
            self.session.execute(
                select(DocumentChunkModel.id).where(DocumentChunkModel.document_id == document_id)
            ).scalars()
        )
        if not chunk_ids:
            return 0

        self.session.execute(
            delete(ConceptDefinitionModel).where(ConceptDefinitionModel.chunk_id.in_(chunk_ids))
        )
        self.session.execute(
            delete(ConceptChunkLinkModel).where(ConceptChunkLinkModel.chunk_id.in_(chunk_ids))
        )
        for chunk_id in chunk_ids:
            self.session.execute(
                delete(EmbeddingModel).where(
                    EmbeddingModel.entity_type == "chunk",
                    EmbeddingModel.entity_id == chunk_id,
                )
            )
        result = self.session.execute(
            delete(DocumentChunkModel).where(DocumentChunkModel.document_id == document_id)
        )
        return result.rowcount  # type: ignore[return-value]

    def save_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> list[DocumentChunkModel]:
        models: list[DocumentChunkModel] = []
        for chunk in chunks:
            model = DocumentChunkModel(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_normalized=chunk.content_normalized,
                chapter=(chunk.chapter[:512] if chunk.chapter else None),
                section=(chunk.section[:512] if chunk.section else None),
                heading_path=chunk.heading_path,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                chunk_type=chunk.chunk_type,
                token_count=chunk.token_count,
                content_hash=chunk.content_hash,
            )
            self.session.add(model)
            models.append(model)
        self.session.flush()

        for model in models:
            self.session.execute(
                text(
                    "UPDATE document_chunks SET fts_vector = to_tsvector('spanish', content_normalized) "
                    "WHERE id = :id"
                ),
                {"id": model.id},
            )

        return models

    def save_embeddings(
        self,
        chunk_models: list[DocumentChunkModel],
        vectors: list[list[float]],
        model_name: str,
        dimensions: int,
    ) -> int:
        saved = 0
        for chunk_model, vector in zip(chunk_models, vectors, strict=True):
            if all(v == 0.0 for v in vector):
                continue
            existing = self.session.execute(
                select(EmbeddingModel).where(
                    EmbeddingModel.entity_type == "chunk",
                    EmbeddingModel.entity_id == chunk_model.id,
                    EmbeddingModel.model == model_name,
                )
            ).scalar_one_or_none()

            if existing:
                existing.vector = vector
            else:
                self.session.add(
                    EmbeddingModel(
                        entity_type="chunk",
                        entity_id=chunk_model.id,
                        model=model_name,
                        dimensions=dimensions,
                        vector=vector,
                    )
                )
            saved += 1
        return saved

    def count_chunks(self, document_id: UUID) -> int:
        result = self.session.execute(
            select(func.count(DocumentChunkModel.id)).where(
                DocumentChunkModel.document_id == document_id
            )
        )
        return result.scalar() or 0
