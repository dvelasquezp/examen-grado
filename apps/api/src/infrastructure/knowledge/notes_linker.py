"""Vincula chunks de Apuntes a conceptos existentes (sin crear definiciones)."""

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID

from src.domain.catalog.enums import DocumentType, SourceRole
from src.domain.knowledge.concept import Concept
from src.domain.knowledge.provenance import build_link_provenance


@dataclass
class LinkCandidate:
    concept_id: UUID
    concept_title: str
    chunk_id: UUID
    document_id: UUID
    document_filename: str
    page_number: int | None
    match_type: str
    relevance_score: float
    excerpt: str


class NotesConceptLinker:
    """Detecta menciones de conceptos canónicos en Apuntes."""

    MIN_TITLE_LENGTH = 4
    EXCERPT_RADIUS = 180

    def find_links(
        self,
        concepts: list[Concept],
        chunks: list[tuple[str, UUID, UUID, str, int | None]],
    ) -> list[LinkCandidate]:
        """
        chunks: list of (content, chunk_id, document_id, document_filename, page_start)
        """
        indexed = self._index_concepts(concepts)
        results: list[LinkCandidate] = []

        for content, chunk_id, document_id, filename, page_start in chunks:
            normalized_content = self._normalize(content)
            seen_concepts: set[UUID] = set()

            for concept_id, title, pattern in indexed:
                if concept_id in seen_concepts:
                    continue
                if not pattern.search(normalized_content):
                    continue

                raw_matches = list(pattern.finditer(normalized_content))
                if not raw_matches:
                    continue
                relevance = min(1.0, 0.75 + 0.05 * len(raw_matches))
                excerpt = self._build_excerpt(normalized_content, raw_matches[0].start())
                seen_concepts.add(concept_id)

                results.append(
                    LinkCandidate(
                        concept_id=concept_id,
                        concept_title=title,
                        chunk_id=chunk_id,
                        document_id=document_id,
                        document_filename=filename,
                        page_number=page_start,
                        match_type="TITLE_MENTION",
                        relevance_score=relevance,
                        excerpt=excerpt,
                    )
                )

        return results

    def _index_concepts(self, concepts: list[Concept]) -> list[tuple[UUID, str, re.Pattern[str]]]:
        indexed: list[tuple[UUID, str, re.Pattern[str]]] = []
        for concept in concepts:
            if not concept.id or not concept.title:
                continue
            title = concept.title.strip()
            if len(title) < self.MIN_TITLE_LENGTH:
                continue
            pattern = self._title_pattern(title)
            if pattern:
                indexed.append((concept.id, title, pattern))
        indexed.sort(key=lambda item: len(item[1]), reverse=True)
        return indexed

    def _title_pattern(self, title: str) -> re.Pattern[str] | None:
        normalized = self._normalize(title)
        if len(normalized) < self.MIN_TITLE_LENGTH:
            return None
        escaped = re.escape(normalized)
        return re.compile(rf"\b{escaped}\b", re.IGNORECASE)

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"\s+", " ", text.strip())

    def _build_excerpt(self, content: str, match_start: int) -> str:
        start = max(0, match_start - self.EXCERPT_RADIUS // 2)
        end = min(len(content), match_start + self.EXCERPT_RADIUS // 2)
        excerpt = content[start:end].strip()
        if start > 0:
            excerpt = "…" + excerpt
        if end < len(content):
            excerpt = excerpt + "…"
        return excerpt[:500]

    @staticmethod
    def candidate_to_provenance(candidate: LinkCandidate) -> dict:
        return build_link_provenance(
            excerpt=candidate.excerpt,
            source_document=candidate.document_filename,
            document_type=DocumentType.LECTURE_NOTES,
            source_role=SourceRole.DOCTRINE,
            page=candidate.page_number,
            chunk_id=candidate.chunk_id,
            match_type=candidate.match_type,
            relevance=candidate.relevance_score,
            concept_title=candidate.concept_title,
        )
