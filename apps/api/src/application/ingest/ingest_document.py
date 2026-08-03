"""Caso de uso: ingerir un documento."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from src.config.settings import Settings
from src.domain.catalog.enums import IngestionStatus
from src.domain.ingestion.chunk import DocumentChunk, ExtractedDocument
from src.infrastructure.ai.embedder import EmbeddingService
from src.infrastructure.documents.chunker import DocumentChunker
from src.infrastructure.documents.deduplicator import ChunkDeduplicator
from src.infrastructure.documents.extractor_factory import DocumentExtractorFactory
from src.infrastructure.persistence.postgres.ingestion_repository import IngestionRepository


@dataclass
class IngestDocumentResult:
    document_id: UUID
    filename: str
    status: str
    chunks_created: int
    embeddings_created: int
    page_count: int
    skipped: bool = False
    error: str | None = None


class IngestDocumentUseCase:
    def __init__(
        self,
        settings: Settings,
        repository: IngestionRepository,
        embedder: EmbeddingService | None = None,
    ):
        self.settings = settings
        self.repository = repository
        self.extractor_factory = DocumentExtractorFactory()
        self.chunker = DocumentChunker()
        self.deduplicator = ChunkDeduplicator()
        self.embedder = embedder or EmbeddingService(settings)

    def execute(self, document_id: UUID, force: bool = False) -> IngestDocumentResult:
        document = self.repository.get_document(document_id)
        if not document:
            return IngestDocumentResult(
                document_id=document_id,
                filename="",
                status="failed",
                chunks_created=0,
                embeddings_created=0,
                page_count=0,
                error="Documento no encontrado",
            )

        if (
            not force
            and document.ingestion_status == IngestionStatus.COMPLETED
        ):
            return IngestDocumentResult(
                document_id=document_id,
                filename=document.filename,
                status="skipped",
                chunks_created=self.repository.count_chunks(document_id),
                embeddings_created=0,
                page_count=document.page_count or 0,
                skipped=True,
            )

        filepath = Path(self.settings.content_path) / document.filepath
        filename = document.filename

        if not filepath.exists():
            self.repository.set_document_status(document, IngestionStatus.FAILED)
            return IngestDocumentResult(
                document_id=document_id,
                filename=document.filename,
                status="failed",
                chunks_created=0,
                embeddings_created=0,
                page_count=0,
                error=f"Archivo no encontrado: {filepath}",
            )

        run = self.repository.create_ingestion_run(document_id)
        self.repository.set_document_status(document, IngestionStatus.PROCESSING)

        try:
            extracted = self.extractor_factory.extract(
                filepath,
                document_type=document.document_type,
            )
            if document.document_type.value == "FLASHCARDS":
                chunks = self._chunk_flashcards(extracted)
            else:
                chunks = self.chunker.chunk(extracted)
            chunks = self.deduplicator.deduplicate(chunks)

            self.repository.delete_document_chunks(document_id)
            chunk_models = self.repository.save_chunks(document_id, chunks)

            embeddings_created = 0
            if self.embedder.enabled and chunk_models:
                texts = [
                    self._chunk_embed_text(c.heading_path, c.content_normalized)
                    for c in chunks
                ]
                vectors = self.embedder.embed_texts(texts)
                embeddings_created = self.repository.save_embeddings(
                    chunk_models,
                    vectors,
                    self.embedder.model_name,
                    self.embedder.dimensions,
                )

            self.repository.set_document_status(
                document,
                IngestionStatus.COMPLETED,
                page_count=extracted.page_count or None,
            )
            self.repository.complete_ingestion_run(
                run,
                status=IngestionStatus.COMPLETED,
                stats={
                    "chunks_created": len(chunks),
                    "embeddings_created": embeddings_created,
                    "page_count": extracted.page_count,
                    "source_role": document.source_role.value,
                },
            )

            return IngestDocumentResult(
                document_id=document_id,
                filename=document.filename,
                status=IngestionStatus.COMPLETED,
                chunks_created=len(chunks),
                embeddings_created=embeddings_created,
                page_count=extracted.page_count,
            )

        except Exception as e:
            self.repository.session.rollback()
            document = self.repository.get_document(document_id)
            if document:
                run = self.repository.create_ingestion_run(document_id)
                self.repository.set_document_status(document, IngestionStatus.FAILED)
                self.repository.complete_ingestion_run(
                    run,
                    status=IngestionStatus.FAILED,
                    errors={"message": str(e)},
                )
            return IngestDocumentResult(
                document_id=document_id,
                filename=filename,
                status=IngestionStatus.FAILED,
                chunks_created=0,
                embeddings_created=0,
                page_count=0,
                error=str(e),
            )

    @staticmethod
    def _chunk_embed_text(heading_path: list[str] | None, content: str) -> str:
        if heading_path:
            return f"[{' > '.join(heading_path)}] {content}"
        return content

    @staticmethod
    def _chunk_flashcards(extracted: ExtractedDocument) -> list[DocumentChunk]:
        import hashlib

        from src.infrastructure.documents.normalizer import (
            estimate_tokens,
            normalize_for_hash,
            normalize_text,
        )

        chunks: list[DocumentChunk] = []
        for block in extracted.blocks:
            normalized = normalize_text(block.text)
            if len(normalized) < 15:
                continue
            chunks.append(
                DocumentChunk(
                    chunk_index=len(chunks),
                    content=block.text,
                    content_normalized=normalized,
                    chapter=None,
                    section=None,
                    heading_path=None,
                    page_start=block.page_number,
                    page_end=block.page_number,
                    chunk_type="flashcard",
                    token_count=estimate_tokens(normalized),
                    content_hash=hashlib.sha256(
                        normalize_for_hash(normalized).encode()
                    ).hexdigest(),
                )
            )
        return chunks
