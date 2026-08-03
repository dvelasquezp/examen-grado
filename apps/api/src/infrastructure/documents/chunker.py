"""División de bloques en chunks con estructura."""

import hashlib
import re

from src.domain.ingestion.chunk import DocumentChunk, ExtractedBlock, ExtractedDocument
from src.infrastructure.documents.normalizer import (
    estimate_tokens,
    normalize_for_hash,
    normalize_text,
    truncate_field,
)

DEFAULT_MAX_CHARS = 3000
DEFAULT_MIN_CHARS = 200


class DocumentChunker:
    def __init__(self, max_chars: int = DEFAULT_MAX_CHARS, min_chars: int = DEFAULT_MIN_CHARS):
        self.max_chars = max_chars
        self.min_chars = min_chars

    def chunk(self, extracted: ExtractedDocument) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        heading_path: list[str] = []
        current_chapter: str | None = None
        current_section: str | None = None
        buffer: list[ExtractedBlock] = []
        buffer_chars = 0

        def flush_buffer():
            nonlocal buffer, buffer_chars
            if not buffer:
                return
            content = "\n\n".join(b.text for b in buffer)
            normalized = normalize_text(content)
            if len(normalized) < 10:
                buffer = []
                buffer_chars = 0
                return

            page_numbers = [b.page_number for b in buffer if b.page_number]
            chunks.append(
                DocumentChunk(
                    chunk_index=len(chunks),
                    content=content,
                    content_normalized=normalized,
                    chapter=truncate_field(current_chapter),
                    section=truncate_field(current_section),
                    heading_path=[t for t in (truncate_field(h) for h in heading_path) if t]
                    if heading_path
                    else None,
                    page_start=min(page_numbers) if page_numbers else None,
                    page_end=max(page_numbers) if page_numbers else None,
                    chunk_type=self._infer_chunk_type(buffer),
                    token_count=estimate_tokens(normalized),
                    content_hash=hashlib.sha256(normalize_for_hash(normalized).encode()).hexdigest(),
                )
            )
            buffer = []
            buffer_chars = 0

        for block in extracted.blocks:
            if block.block_type == "heading":
                flush_buffer()
                title = truncate_field(normalize_text(block.text), max_len=500) or normalize_text(block.text)[:500]
                if block.heading_level == 1 or (title and "CAP" in title.upper()):
                    current_chapter = title
                    current_section = None
                    heading_path = [title]
                else:
                    current_section = title
                    if heading_path:
                        heading_path = heading_path[:1] + [title]
                    else:
                        heading_path = [title]
                buffer.append(block)
                buffer_chars += len(block.text)
                continue

            if buffer_chars + len(block.text) > self.max_chars and buffer_chars >= self.min_chars:
                flush_buffer()

            buffer.append(block)
            buffer_chars += len(block.text)

        flush_buffer()
        return chunks

    @staticmethod
    def _infer_chunk_type(blocks: list[ExtractedBlock]) -> str:
        types = {b.block_type for b in blocks}
        if types == {"heading"}:
            return "heading"
        if "list" in types:
            return "list"
        return "paragraph"
