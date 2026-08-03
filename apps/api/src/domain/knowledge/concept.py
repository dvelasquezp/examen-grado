"""Entidades de conocimiento jurídico."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class ProvenanceOrigin:
    source_document: str
    source_type: str
    source_role: str
    page: int | None
    chunk_id: UUID | None
    extraction_method: str
    confidence: float
    display_label: str


@dataclass
class ConceptDefinition:
    text: str
    is_primary: bool
    source_type: str  # EXTRACTED | GENERATED
    document_id: UUID | None
    page_number: int | None
    chunk_id: UUID | None
    confidence: float
    provenance: dict
    display_label: str


@dataclass
class Concept:
    id: UUID | None
    subject_id: UUID
    slug: str
    title: str
    definition: str | None = None
    simple_explanation: str | None = None
    subtopic: str | None = None
    difficulty: int = 3
    importance_score: float = 0.5
    confidence_score: float = 0.0
    definitions: list[ConceptDefinition] = field(default_factory=list)
    neo4j_node_id: str | None = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime | None = None

    @staticmethod
    def slugify(title: str) -> str:
        import re
        import unicodedata

        normalized = unicodedata.normalize("NFKD", title)
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name.lower()).strip("-")
        return slug[:200] or "concepto"
