"""Mapa conceptual desde co-ocurrencias en Apuntes."""

import re
import unicodedata
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MATCHING_MAX_SENTENCES = 3
MATCHING_MAX_CHARS = 550

SENTENCE_START = re.compile(r'^[A-ZÁÉÍÓÚÑÜ0-9«"(]')
SENTENCE_END = re.compile(r'[.;:?)»"\']$')
DEFINITION_START = re.compile(
    r"^(es|son|se entiende|consiste|designa|facultad|derecho|disminución|falsa|terminación)\b",
    re.I,
)
INCOMPLETE_TAIL = re.compile(r"(\.{3}|…|\(Art\.?)$", re.I)


def normalize_matching_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw.strip())
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^…+\s*", "", text)
    text = re.sub(r"\s*…+\s*$", "", text)
    text = re.sub(r"\s*…\s*", " ", text)
    return text.strip()


def _capitalize_if_definition(s: str) -> str:
    if SENTENCE_START.match(s):
        return s
    if DEFINITION_START.match(s):
        return s[0].upper() + s[1:]
    return s


def _is_complete_sentence(s: str) -> bool:
    s = s.strip()
    if len(s) < 20:
        return False
    if INCOMPLETE_TAIL.search(s):
        return False
    if "…" in s or "..." in s:
        return False
    normalized = _capitalize_if_definition(s)
    if not SENTENCE_START.match(normalized.lstrip('«"\'')):
        return False
    if not SENTENCE_END.search(normalized):
        return False
    return True


def _finalize_sentence(s: str) -> str:
    s = _capitalize_if_definition(s.strip())
    if s and s[-1] not in ".;:":
        s += "."
    return s


def split_complete_sentences(raw: str) -> list[str]:
    """Oraciones completas que empiezan en mayúscula y terminan en punto (u otro cierre)."""
    text = normalize_matching_text(raw)
    if not text:
        return []

    sentences: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        candidate = _finalize_sentence(candidate)
        if not _is_complete_sentence(candidate):
            return
        key = candidate.lower()
        if key in seen:
            return
        seen.add(key)
        sentences.append(candidate)

    # Oraciones explícitas separadas por punto y coma
    for part in re.split(r"(?<=[.;:])\s+", text):
        part = part.strip()
        if part:
            add(part)

    # Oraciones embebidas en fragmentos de chunk (p. ej. tras otro enunciado)
    for match in re.finditer(
        r'(?:^|[.;:]\s+)([A-ZÁÉÍÓÚÑÜ«"(][^.!?;:]{15,}[.!?;:])',
        text,
    ):
        add(match.group(1))

    return sentences


def select_sentences(
    sentences: list[str],
    max_sentences: int = MATCHING_MAX_SENTENCES,
    max_chars: int = MATCHING_MAX_CHARS,
) -> str:
    selected: list[str] = []
    total = 0
    for sentence in sentences:
        if total + len(sentence) > max_chars and selected:
            break
        selected.append(sentence)
        total += len(sentence) + 1
        if len(selected) >= max_sentences:
            break
    return " ".join(selected)


def expand_to_sentences(
    raw: str,
    max_sentences: int = MATCHING_MAX_SENTENCES,
    max_chars: int = MATCHING_MAX_CHARS,
) -> str:
    """Devuelve oraciones completas (punto a punto), sin cortar a mitad de frase."""
    return select_sentences(split_complete_sentences(raw), max_sentences, max_chars)


def build_matching_definition(canonical: str | None, excerpt: str | None = None) -> str:
    """Definición en oraciones completas; prioriza canónica y enriquece con apunte válido."""
    canon_sents = split_complete_sentences(canonical or "")
    excerpt_sents = split_complete_sentences(excerpt or "") if excerpt else []

    pool: list[str] = []
    seen: set[str] = set()

    def extend(source: list[str]) -> None:
        for s in source:
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            pool.append(s)

    extend(canon_sents)
    if len(select_sentences(pool)) < 120:
        extend(excerpt_sents)

    result = select_sentences(pool)
    if len(result) >= 30:
        return result

    # Si la canónica quedó vacía por fragmentos, intentar solo apunte limpio
    fallback = select_sentences(excerpt_sents) or select_sentences(canon_sents)
    if len(fallback) >= 30:
        return fallback

    # Último recurso: una sola oración bien formada del texto más largo
    for source in (canonical, excerpt):
        if not source:
            continue
        text = normalize_matching_text(source)
        match = re.search(r"([A-ZÁÉÍÓÚÑÜ«\"(][^.!?;:]{25,}[.!?;:])", text)
        if match and _is_complete_sentence(match.group(1)):
            return _finalize_sentence(match.group(1))

    return fallback


class GraphService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_subject_graph(self, subject_id: UUID, limit: int = 80) -> dict:
        nodes_result = await self.session.execute(
            text("""
                SELECT c.id, c.title, c.slug, c.subtopic,
                       COUNT(l.id) AS link_count
                FROM concepts c
                LEFT JOIN concept_chunk_links l ON l.concept_id = c.id
                WHERE c.subject_id = :subject_id
                GROUP BY c.id
                ORDER BY link_count DESC, c.title
                LIMIT :limit
            """),
            {"subject_id": str(subject_id), "limit": limit},
        )
        nodes = [
            {
                "id": str(row.id),
                "title": row.title,
                "slug": row.slug,
                "subtopic": row.subtopic,
                "link_count": row.link_count or 0,
            }
            for row in nodes_result
        ]
        node_ids = [n["id"] for n in nodes]
        if len(node_ids) < 2:
            return {"nodes": nodes, "edges": []}

        edges_result = await self.session.execute(
            text("""
                SELECT l1.concept_id AS source, l2.concept_id AS target,
                       COUNT(*) AS weight
                FROM concept_chunk_links l1
                JOIN concept_chunk_links l2 ON l1.chunk_id = l2.chunk_id
                    AND l1.concept_id < l2.concept_id
                JOIN concepts c1 ON c1.id = l1.concept_id
                JOIN concepts c2 ON c2.id = l2.concept_id
                WHERE c1.subject_id = :subject_id AND c2.subject_id = :subject_id
                GROUP BY l1.concept_id, l2.concept_id
                HAVING COUNT(*) >= 1
                ORDER BY weight DESC
                LIMIT 150
            """),
            {"subject_id": str(subject_id)},
        )
        edges = [
            {
                "source": str(row.source),
                "target": str(row.target),
                "weight": row.weight,
                "type": "CO_OCCURS_IN_NOTES",
            }
            for row in edges_result
            if str(row.source) in node_ids and str(row.target) in node_ids
        ]
        return {"nodes": nodes, "edges": edges}

    async def get_matching_game_pairs(self, subject_id: UUID, count: int = 6) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT c.id, c.title, c.definition,
                       (
                         SELECT COALESCE(l.excerpt, dc.content)
                         FROM concept_chunk_links l
                         JOIN document_chunks dc ON dc.id = l.chunk_id
                         WHERE l.concept_id = c.id
                         ORDER BY l.relevance_score DESC NULLS LAST
                         LIMIT 1
                       ) AS excerpt
                FROM concepts c
                WHERE c.subject_id = :subject_id
                  AND c.definition IS NOT NULL
                ORDER BY random()
                LIMIT :count
            """),
            {"subject_id": str(subject_id), "count": count},
        )
        pairs = []
        for row in result:
            definition = build_matching_definition(row.definition, row.excerpt)
            if len(definition) < 30:
                continue
            if "…" in definition or "..." in definition:
                continue
            if not definition[0].isupper() and definition[0] not in '«"(':
                continue
            pairs.append(
                {
                    "concept_id": str(row.id),
                    "title": row.title,
                    "definition": definition,
                }
            )
        return pairs
