"""Esquemas Pydantic para la API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.catalog.enums import DocumentType, IngestionStatus, SourceRole


class SubjectResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    folder_path: str
    is_active: bool
    discovered_at: datetime
    document_count: int = 0

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: UUID
    subject_id: UUID | None
    filename: str
    filepath: str
    document_type: DocumentType
    source_role: SourceRole
    file_hash: str
    file_size: int | None
    page_count: int | None
    ingestion_status: IngestionStatus
    last_ingested_at: datetime | None

    model_config = {"from_attributes": True}


class DiscoverResponse(BaseModel):
    subjects_found: int
    documents_found: int
    documents_new: int
    documents_updated: int
    scanned_paths: int
    skipped_paths: int


class HealthResponse(BaseModel):
    status: str
    services: dict[str, str]
    version: str = "0.1.0"


class ModelInfoResponse(BaseModel):
    models: dict[str, str]
    tasks: list[str]


class MaintenanceStatusResponse(BaseModel):
    subjects: int
    documents: int
    documents_by_status: dict[str, int]
    content_path: str
