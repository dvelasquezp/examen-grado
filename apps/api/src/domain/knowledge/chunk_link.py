"""Vínculo entre concepto canónico y chunk de Apuntes."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ConceptChunkLink:
    id: UUID | None
    concept_id: UUID
    chunk_id: UUID
    document_id: UUID
    page_number: int | None
    match_type: str
    relevance_score: float
    excerpt: str | None
    provenance: dict
    document_filename: str | None = None
    chunk_content: str | None = None
    created_at: datetime | None = None
