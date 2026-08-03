"""Esquemas de ingesta."""

from uuid import UUID

from pydantic import BaseModel


class IngestDocumentResponse(BaseModel):
    document_id: UUID
    filename: str
    status: str
    chunks_created: int
    embeddings_created: int
    page_count: int
    skipped: bool = False
    error: str | None = None


class IngestPendingResponse(BaseModel):
    total: int
    completed: int
    failed: int
    skipped: int
    results: list[IngestDocumentResponse]


class IngestionRunResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: str
    started_at: str
    completed_at: str | None
    stats: dict | None
    errors: dict | None
