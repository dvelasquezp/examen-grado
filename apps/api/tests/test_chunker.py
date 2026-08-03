"""Tests del chunker."""

from src.domain.ingestion.chunk import ExtractedBlock, ExtractedDocument
from src.infrastructure.documents.chunker import DocumentChunker
from src.infrastructure.documents.deduplicator import ChunkDeduplicator


def test_chunker_preserves_headings():
    extracted = ExtractedDocument(
        blocks=[
            ExtractedBlock(text="CAPÍTULO I", block_type="heading", heading_level=1, page_number=1),
            ExtractedBlock(text="Texto del capítulo uno.", page_number=1),
            ExtractedBlock(text="Sección 1.1", block_type="heading", heading_level=2, page_number=2),
            ExtractedBlock(text="Contenido de la sección.", page_number=2),
        ],
        page_count=2,
    )
    chunker = DocumentChunker(max_chars=5000)
    chunks = chunker.chunk(extracted)
    assert len(chunks) >= 1
    assert chunks[0].chapter == "CAPÍTULO I"
    assert chunks[0].heading_path is not None


def test_deduplicator_removes_duplicates():
    from src.domain.ingestion.chunk import DocumentChunk

    chunks = [
        DocumentChunk(
            chunk_index=0,
            content="Same text",
            content_normalized="same text",
            content_hash="abc123",
        ),
        DocumentChunk(
            chunk_index=1,
            content="Same text",
            content_normalized="same text",
            content_hash="abc123",
        ),
        DocumentChunk(
            chunk_index=2,
            content="Different",
            content_normalized="different",
            content_hash="def456",
        ),
    ]
    dedup = ChunkDeduplicator()
    result = dedup.deduplicate(chunks)
    assert len(result) == 2
    assert result[0].chunk_index == 0
    assert result[1].chunk_index == 1
