"""Esquemas de conceptos y búsqueda."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProvenanceStatementResponse(BaseModel):
    text: str
    display_label: str
    source_document: str | None = None
    source_type: str | None = None
    page: int | None = None
    confidence: float | None = None
    extraction_method: str | None = None


class ConceptDefinitionResponse(BaseModel):
    id: UUID | None = None
    text: str
    is_primary: bool
    source_type: str
    page_number: int | None
    confidence: float
    provenance: dict
    display_label: str = ""


class ConceptSummaryResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    definition: str | None
    subtopic: str | None
    difficulty: int
    confidence_score: float
    definition_count: int = 0


class ConceptNoteReferenceResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID | None = None
    document_filename: str
    page_number: int | None
    match_type: str
    relevance_score: float
    excerpt: str | None
    display_label: str = "Mención en Apuntes"


class ChunkDetailResponse(BaseModel):
    chunk_id: UUID
    content: str
    page_start: int | None
    page_end: int | None
    chapter: str | None
    section: str | None
    heading_path: list[str] | None
    chunk_type: str | None
    document_id: UUID
    document_filename: str
    document_filepath: str
    document_type: str
    page_count: int | None
    excerpt: str | None = None
    relevance_score: float | None = None
    match_type: str | None = None
    highlight_term: str | None = None
    concept_id: UUID | None = None
    concept_title: str | None = None
    concept_slug: str | None = None


class ConceptDetailResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    definition: str | None
    simple_explanation: str | None
    practical_case: str | None = None
    subtopic: str | None
    difficulty: int
    importance_score: float
    confidence_score: float
    definitions: list[ConceptDefinitionResponse]
    note_references: list[ConceptNoteReferenceResponse] = Field(default_factory=list)
    created_at: datetime | None


class ExtractConceptsResponse(BaseModel):
    subject_slug: str
    candidates_found: int
    concepts_created: int
    concepts_updated: int
    definitions_added: int


class LinkNotesResponse(BaseModel):
    subject_slug: str
    concepts_total: int
    chunks_scanned: int
    links_found: int
    links_created: int
    links_skipped: int


class ClassifyAreasResponse(BaseModel):
    subject_slug: str
    concepts_total: int
    with_evidence: int
    unassigned: int
    areas: dict[str, int]


class EnrichDefinitionsResponse(BaseModel):
    subject_slug: str
    concepts_total: int
    memorizador_path: str
    entries_scanned: int
    enriched: int
    titles_fixed: int
    unchanged: int
    examples: list[str]


class ImportExcelDefinitionsResponse(BaseModel):
    subject_slug: str
    excel_rows: int
    updated: int
    created: int
    unchanged: int
    unmatched: int
    pruned: int = 0
    examples: list[str]


class ResetConceptsResponse(BaseModel):
    subject_slug: str
    concepts_deleted: int
    definitions_deleted: int
    links_deleted: int


class SearchResultItem(BaseModel):
    id: str
    title: str
    slug: str
    definition: str | None = None
    subtopic: str | None = None
    score: float = 0.0
    match_type: str = "keyword"
    final_score: float | None = None


class ChunkSearchResult(BaseModel):
    chunk_id: str
    content: str
    page_start: int | None
    page_end: int | None
    filename: str
    document_type: str
    score: float


class SearchResponse(BaseModel):
    query: str
    total: int
    concepts: list[SearchResultItem]
    chunks: list[ChunkSearchResult] = Field(default_factory=list)
