"""Entidad de documento."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.catalog.enums import DocumentType, IngestionStatus, SourceRole


@dataclass
class Document:
    id: UUID | None
    subject_id: UUID | None
    filename: str
    filepath: str
    document_type: DocumentType
    source_role: SourceRole
    file_hash: str
    file_size: int | None = None
    page_count: int | None = None
    ingestion_status: IngestionStatus = IngestionStatus.PENDING
    last_ingested_at: datetime | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_doctrine(self) -> bool:
        return self.source_role == SourceRole.DOCTRINE

    @property
    def is_exam_pattern_only(self) -> bool:
        return self.source_role == SourceRole.EXAM_PATTERN_ONLY
