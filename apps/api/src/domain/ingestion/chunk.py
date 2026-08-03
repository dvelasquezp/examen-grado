"""Bloques extraídos de documentos."""

from dataclasses import dataclass, field


@dataclass
class ExtractedBlock:
    text: str
    page_number: int | None = None
    block_type: str = "paragraph"
    heading_level: int | None = None


@dataclass
class ExtractedDocument:
    blocks: list[ExtractedBlock] = field(default_factory=list)
    page_count: int = 0


@dataclass
class DocumentChunk:
    chunk_index: int
    content: str
    content_normalized: str
    chapter: str | None = None
    section: str | None = None
    heading_path: list[str] | None = None
    page_start: int | None = None
    page_end: int | None = None
    chunk_type: str = "paragraph"
    token_count: int = 0
    content_hash: str = ""
