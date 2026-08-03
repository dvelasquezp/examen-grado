"""Extracción basada en reglas desde chunks."""

import re
from dataclasses import dataclass
from uuid import UUID

from src.domain.catalog.enums import DocumentType, SourceRole
from src.domain.knowledge.provenance import build_provenance

DEFINITION_PATTERNS = [
    re.compile(
        r"(?:se entiende por|se define como|es aquel|es aquella|consiste en)\s+"
        r"[«\"']?(?P<title>[A-ZÁÉÍÓÚÑa-záéíóúñ\s\-]{3,80})[»\"']?\s+"
        r"(?P<def>.{30,800}?)(?:\.|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^(?P<title>[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s\-]{2,80})\s*[\:\-–—]\s*(?P<def>.{30,800})$",
        re.MULTILINE,
    ),
    re.compile(
        r"^Definici[oó]n[\:\s]+(?P<def>.{30,800})$",
        re.IGNORECASE | re.MULTILINE,
    ),
]

FLASHCARD_PAIR_PATTERN = re.compile(
    r"^(?P<front>.{3,200}?)\n(?P<back>.{20,2000})$",
    re.MULTILINE | re.DOTALL,
)

FLASHCARD_INLINE_PATTERN = re.compile(
    r"^(?P<title>.{3,120}?)\s*[\:\-–—]\s*(?P<def>.{20,1500})$",
    re.MULTILINE,
)


@dataclass
class ExtractedConceptCandidate:
    title: str
    definition: str
    document_id: UUID
    document_filename: str
    document_type: DocumentType
    source_role: SourceRole
    chunk_id: UUID
    page_number: int | None
    extraction_method: str
    confidence: float
    subtopic: str | None = None


class RuleBasedConceptExtractor:
    """Extrae candidatos a concepto solo desde Flashcards (fuente canónica)."""

    CANONICAL_TYPES = {DocumentType.FLASHCARDS}

    def extract_from_chunk(
        self,
        content: str,
        *,
        document_id: UUID,
        document_filename: str,
        document_type: DocumentType,
        source_role: SourceRole,
        chunk_id: UUID,
        page_start: int | None,
        chapter: str | None,
        section: str | None,
    ) -> list[ExtractedConceptCandidate]:
        if source_role != SourceRole.DOCTRINE:
            return []
        if document_type not in self.CANONICAL_TYPES:
            return []

        subtopic = section or chapter
        candidates = self._extract_flashcards(
            content,
            document_id=document_id,
            document_filename=document_filename,
            document_type=document_type,
            source_role=source_role,
            chunk_id=chunk_id,
            page_start=page_start,
            subtopic=subtopic,
        )
        return self._dedupe_candidates(candidates)

    def _extract_flashcards(self, content: str, **kwargs) -> list[ExtractedConceptCandidate]:
        results: list[ExtractedConceptCandidate] = []
        for block in re.split(r"\n{2,}", content):
            block = block.strip()
            if len(block) < 25:
                continue

            matched = False
            for pattern in (FLASHCARD_PAIR_PATTERN, FLASHCARD_INLINE_PATTERN):
                for m in pattern.finditer(block):
                    title = self._clean_title(m.groupdict().get("title") or m.groupdict().get("front", ""))
                    definition = self._clean_definition(
                        m.groupdict().get("def") or m.groupdict().get("back", "")
                    )
                    if self._is_valid_pair(title, definition):
                        results.append(self._make_candidate(title, definition, confidence=0.92, **kwargs))
                        matched = True
            if not matched:
                lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
                if len(lines) >= 2 and len(lines[0]) < 120 and len(lines[1]) > 30:
                    title = self._clean_title(lines[0])
                    definition = self._clean_definition("\n".join(lines[1:3]))
                    if self._is_valid_pair(title, definition):
                        results.append(self._make_candidate(title, definition, confidence=0.85, **kwargs))
        return results

    def _extract_definitions(self, content: str, **kwargs) -> list[ExtractedConceptCandidate]:
        results: list[ExtractedConceptCandidate] = []
        for pattern in DEFINITION_PATTERNS:
            for m in pattern.finditer(content):
                groups = m.groupdict()
                title = self._clean_title(groups.get("title", ""))
                definition = self._clean_definition(groups.get("def", ""))
                if title and self._is_valid_pair(title, definition):
                    results.append(self._make_candidate(title, definition, confidence=0.78, **kwargs))
                elif not title and definition:
                    title = self._title_from_definition(definition)
                    if self._is_valid_pair(title, definition):
                        results.append(self._make_candidate(title, definition, confidence=0.65, **kwargs))
        return results

    def _make_candidate(self, title: str, definition: str, confidence: float, **kwargs) -> ExtractedConceptCandidate:
        return ExtractedConceptCandidate(
            title=title,
            definition=definition,
            document_id=kwargs["document_id"],
            document_filename=kwargs["document_filename"],
            document_type=kwargs["document_type"],
            source_role=kwargs["source_role"],
            chunk_id=kwargs["chunk_id"],
            page_number=kwargs.get("page_start"),
            extraction_method="RULE_BASED",
            confidence=confidence,
            subtopic=kwargs.get("subtopic"),
        )

    @staticmethod
    def _clean_title(text: str) -> str:
        text = re.sub(r"\s+", " ", text.strip())
        text = text.strip(":-–—. ")
        return text[:200]

    @staticmethod
    def _clean_definition(text: str) -> str:
        text = re.sub(r"\s+", " ", text.strip())
        return text[:2000]

    @staticmethod
    def _is_valid_pair(title: str, definition: str) -> bool:
        if not title or not definition:
            return False
        if len(title) < 3 or len(definition) < 20:
            return False
        if not title[0].isupper():
            return False
        if title.lower() == definition.lower()[: len(title)].lower():
            return False
        if len(title.split()) > 15:
            return False
        if re.search(r"^\d+\.?\s", title):
            return False
        fragment_patterns = (
            r"^(acontecer|regular la|que se|en virtud|anacomen|ciento)\b",
            r"\b(una cosa|la negativa)\b",
        )
        lowered = title.lower()
        if any(re.search(p, lowered) for p in fragment_patterns):
            return False
        return True

    @staticmethod
    def _title_from_definition(definition: str) -> str:
        words = definition.split()[:6]
        return " ".join(words).rstrip(",.;:")

    @staticmethod
    def _dedupe_candidates(candidates: list[ExtractedConceptCandidate]) -> list[ExtractedConceptCandidate]:
        seen: set[tuple[str, str]] = set()
        unique: list[ExtractedConceptCandidate] = []
        for c in candidates:
            key = (c.title.lower(), c.definition[:100].lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(c)
        return unique


def candidate_to_provenance(candidate: ExtractedConceptCandidate) -> dict:
    return build_provenance(
        text=candidate.definition,
        source_document=candidate.document_filename,
        document_type=candidate.document_type,
        source_role=candidate.source_role,
        page=candidate.page_number,
        chunk_id=candidate.chunk_id,
        extraction_method=candidate.extraction_method,
        confidence=candidate.confidence,
    )
