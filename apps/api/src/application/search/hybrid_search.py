"""Búsqueda híbrida: FTS + semántica."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings
from src.infrastructure.ai.embedder import EmbeddingService
from src.infrastructure.persistence.postgres.concept_repository import ConceptRepository


class HybridSearchService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings
        self.concept_repo = ConceptRepository(session)
        self.embedder = EmbeddingService(settings)

    async def search(
        self,
        query: str,
        subject_id: UUID | None = None,
        limit: int = 20,
    ) -> dict:
        if not query.strip():
            return {"query": query, "results": [], "total": 0}

        fts_results = await self.concept_repo.search_fts(query, subject_id, limit=limit)
        semantic_results = await self._semantic_search(query, subject_id, limit=limit)

        merged = self._merge_results(fts_results, semantic_results, limit=limit)
        chunk_results = await self._search_chunks(query, subject_id, limit=10)

        return {
            "query": query,
            "total": len(merged),
            "concepts": merged,
            "chunks": chunk_results,
        }

    async def _semantic_search(
        self, query: str, subject_id: UUID | None, limit: int
    ) -> list[dict]:
        if not self.embedder.enabled:
            return []

        vector = self.embedder.embed_query(query)
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"

        sql = text("""
            SELECT c.id, c.title, c.slug, c.definition, c.subtopic,
                   1 - (e.vector <=> :vector::vector) AS score
            FROM embeddings e
            JOIN concepts c ON c.id = e.entity_id AND e.entity_type = 'concept'
            WHERE (:subject_id::uuid IS NULL OR c.subject_id = :subject_id)
            ORDER BY e.vector <=> :vector::vector
            LIMIT :limit
        """)
        try:
            result = await self.session.execute(
                sql,
                {
                    "vector": vector_str,
                    "subject_id": str(subject_id) if subject_id else None,
                    "limit": limit,
                },
            )
            return [
                {
                    "id": str(row.id),
                    "title": row.title,
                    "slug": row.slug,
                    "definition": row.definition,
                    "subtopic": row.subtopic,
                    "score": float(row.score),
                    "match_type": "semantic",
                }
                for row in result
            ]
        except Exception:
            return []

    async def _search_chunks(
        self, query: str, subject_id: UUID | None, limit: int
    ) -> list[dict]:
        sql = text("""
            SELECT dc.id, dc.content_normalized, dc.page_start, dc.page_end,
                   d.filename, d.filepath, d.document_type,
                   ts_rank_cd(dc.fts_vector, plainto_tsquery('spanish', :q)) AS rank
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.fts_vector @@ plainto_tsquery('spanish', :q)
            AND d.source_role = 'DOCTRINE'
            AND (:subject_id::uuid IS NULL OR d.subject_id = :subject_id)
            ORDER BY rank DESC
            LIMIT :limit
        """)
        result = await self.session.execute(
            sql,
            {"q": query, "subject_id": str(subject_id) if subject_id else None, "limit": limit},
        )
        return [
            {
                "chunk_id": str(row.id),
                "content": (row.content_normalized or "")[:300],
                "page_start": row.page_start,
                "page_end": row.page_end,
                "filename": row.filename,
                "document_type": row.document_type,
                "score": float(row.rank),
                "match_type": "chunk",
            }
            for row in result
        ]

    @staticmethod
    def _merge_results(
        fts: list[dict], semantic: list[dict], limit: int
    ) -> list[dict]:
        scores: dict[str, dict] = {}
        for item in fts:
            cid = item["id"]
            scores[cid] = {**item, "final_score": item["score"] * 0.4}
        for item in semantic:
            cid = item["id"]
            if cid in scores:
                scores[cid]["final_score"] += item["score"] * 0.35
                scores[cid]["match_type"] = "hybrid"
            else:
                scores[cid] = {**item, "final_score": item["score"] * 0.35}
        ranked = sorted(scores.values(), key=lambda x: x["final_score"], reverse=True)
        return ranked[:limit]
