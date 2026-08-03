"""Deduplicación de chunks."""

from src.domain.ingestion.chunk import DocumentChunk


class ChunkDeduplicator:
    def deduplicate(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        seen_hashes: set[str] = set()
        unique: list[DocumentChunk] = []

        for chunk in chunks:
            if chunk.content_hash in seen_hashes:
                continue
            seen_hashes.add(chunk.content_hash)
            chunk.chunk_index = len(unique)
            unique.append(chunk)

        return unique
