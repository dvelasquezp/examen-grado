"""Generador de ejercicios completar concepto desde Apuntes."""

import random
import re
import unicodedata
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

BLANK = "________"
PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")
HEADING_ROMAN = re.compile(r"^[IVXLC]+\)\s", re.IGNORECASE)
HEADING_NUMBERED = re.compile(r"^\d+\.\s")
MAX_PARAGRAPHS_AFTER = 5
MAX_CONTEXT_CHARS = 2200
MIN_CONTEXT_LEN = 80
MIN_TERM_LEN = 5


class FillBlankGenerator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_exercises(self, subject_id: UUID, count: int = 10) -> list[dict]:
        rows = await self.session.execute(
            text("""
                SELECT l.chunk_id, l.excerpt, c.id AS concept_id, c.title,
                       dc.content AS chunk_content, d.filename
                FROM concept_chunk_links l
                JOIN concepts c ON c.id = l.concept_id
                JOIN document_chunks dc ON dc.id = l.chunk_id
                JOIN documents d ON d.id = l.document_id
                WHERE c.subject_id = :subject_id
                  AND d.document_type = 'LECTURE_NOTES'
                ORDER BY random()
                LIMIT 120
            """),
            {"subject_id": str(subject_id)},
        )
        candidates: list[dict] = []
        seen: set[str] = set()

        all_rows = list(rows)
        chunk_concepts: dict[str, list[tuple[str, str]]] = {}
        for row in all_rows:
            cid = str(row.chunk_id)
            chunk_concepts.setdefault(cid, [])
            entry = (str(row.concept_id), row.title)
            if entry not in chunk_concepts[cid]:
                chunk_concepts[cid].append(entry)

        chunk_ids = list(chunk_concepts.keys())
        if chunk_ids:
            extra = await self.session.execute(
                text("""
                    SELECT l.chunk_id, c.id, c.title
                    FROM concept_chunk_links l
                    JOIN concepts c ON c.id = l.concept_id
                    WHERE c.subject_id = :subject_id
                      AND l.chunk_id IN :chunk_ids
                """).bindparams(bindparam("chunk_ids", expanding=True)),
                {"subject_id": str(subject_id), "chunk_ids": chunk_ids},
            )
            for row in extra:
                cid = str(row.chunk_id)
                entry = (str(row.id), row.title)
                if entry not in chunk_concepts.setdefault(cid, []):
                    chunk_concepts[cid].append(entry)

        for row in all_rows:
            chunk_id = str(row.chunk_id)
            text_source = row.chunk_content or row.excerpt or ""
            concepts_in_chunk = chunk_concepts.get(chunk_id, [(str(row.concept_id), row.title)])
            exercise = self._build_from_text(
                text_source,
                str(row.concept_id),
                row.title,
                concepts_in_chunk,
                chunk_id,
                row.filename,
            )
            if exercise and exercise["id"] not in seen:
                seen.add(exercise["id"])
                candidates.append(exercise)

        random.shuffle(candidates)
        return candidates[:count]

    def _build_from_text(
        self,
        content: str,
        prompt_concept_id: str,
        prompt_title: str,
        concepts_in_chunk: list[tuple[str, str]],
        chunk_id: str,
        source: str,
    ) -> dict | None:
        if len(content.strip()) < MIN_CONTEXT_LEN:
            return None

        paragraphs = self._paragraphs(content)
        if not paragraphs:
            return None

        blank_choice = self._pick_blank_term(content, paragraphs, concepts_in_chunk, prompt_concept_id)
        if not blank_choice:
            return None

        answer_id, answer_title, para_idx = blank_choice
        context_text = self._extract_from_paragraph(paragraphs, para_idx, answer_title)
        if not context_text:
            return None

        masked = self._mask_term(context_text, answer_title)
        if BLANK not in masked:
            return None

        section_label = self._section_label(paragraphs, para_idx)

        return {
            "id": f"{chunk_id}:{answer_id}:{hash(masked) & 0xFFFF}",
            "prompt": masked,
            "sentence": masked,
            "answer": answer_title,
            "concept_id": answer_id,
            "concept_title": section_label or answer_title,
            "chunk_id": chunk_id,
            "source": source,
        }

    def _pick_blank_term(
        self,
        content: str,
        paragraphs: list[str],
        concepts_in_chunk: list[tuple[str, str]],
        prompt_concept_id: str,
    ) -> tuple[str, str, int] | None:
        """Elige qué concepto enmascarar y en qué párrafo (evita títulos partidos)."""
        candidates: list[tuple[str, str, int, int]] = []

        for cid, title in concepts_in_chunk:
            if len(title.strip()) < MIN_TERM_LEN:
                continue
            if not self._contains_term(content, title):
                continue

            pattern = re.compile(re.escape(title), re.IGNORECASE)
            for idx, para in enumerate(paragraphs):
                if not pattern.search(para):
                    continue
                if self._is_bad_blank_paragraph(para, title):
                    continue
                # Preferir párrafos de cuerpo; desempate: no el prompt si hay otro
                score = 0
                if not self._is_heading_paragraph(para):
                    score += 10
                if cid != prompt_concept_id:
                    score += 5
                if len(para) > 120:
                    score += 3
                candidates.append((score, cid, title, idx))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        top_score = candidates[0][0]
        best = [c for c in candidates if c[0] >= top_score - 2]
        _, cid, title, idx = random.choice(best)
        return cid, title, idx

    def _extract_from_paragraph(
        self, paragraphs: list[str], start_idx: int, term: str
    ) -> str | None:
        """Desde el punto aparte del blanco hacia adelante; incluye el título de sección anterior."""
        actual_start = start_idx
        if start_idx > 0 and self._is_heading_paragraph(paragraphs[start_idx - 1]):
            actual_start = start_idx - 1

        selected: list[str] = []
        total = 0

        for para in paragraphs[actual_start : actual_start + MAX_PARAGRAPHS_AFTER]:
            if total + len(para) > MAX_CONTEXT_CHARS and selected:
                break
            selected.append(para)
            total += len(para) + 2

        if not selected:
            return None

        window = "\n\n".join(selected)
        return window if len(window) >= MIN_CONTEXT_LEN else None

    @staticmethod
    def _section_label(paragraphs: list[str], para_idx: int) -> str | None:
        """Título de sección inmediatamente anterior (ej. «II) TESTAMENTO…»)."""
        if FillBlankGenerator._is_heading_paragraph(paragraphs[para_idx]):
            return paragraphs[para_idx]
        if para_idx > 0 and FillBlankGenerator._is_heading_paragraph(paragraphs[para_idx - 1]):
            return paragraphs[para_idx - 1]
        return None

    @staticmethod
    def _paragraphs(content: str) -> list[str]:
        text = unicodedata.normalize("NFKC", content)
        blocks = PARAGRAPH_BREAK.split(text.strip())
        paragraphs: list[str] = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = [re.sub(r"[ \t]+", " ", ln.strip()) for ln in block.split("\n") if ln.strip()]
            if not lines:
                continue

            merged: list[str] = []
            buffer = ""
            for ln in lines:
                if FillBlankGenerator._is_heading_paragraph(ln):
                    if buffer:
                        merged.append(buffer.strip())
                        buffer = ""
                    merged.append(ln)
                    continue

                if not buffer:
                    buffer = ln
                elif FillBlankGenerator._is_soft_wrap_continuation(buffer, ln):
                    buffer = f"{buffer} {ln}"
                else:
                    merged.append(buffer.strip())
                    buffer = ln

            if buffer:
                merged.append(buffer.strip())

            for para in merged:
                if len(para) >= 15:
                    paragraphs.append(para)
        return paragraphs

    @staticmethod
    def _is_soft_wrap_continuation(previous: str, line: str) -> bool:
        """Une saltos de línea del PDF que parten una misma oración."""
        stripped = line.strip()
        if not stripped:
            return False
        if stripped[0].islower():
            return True
        # Fragmento muy corto tras corte (p. ej. «declarado.»)
        if len(stripped) < 24 and not FillBlankGenerator._is_heading_paragraph(stripped):
            prev = previous.rstrip()
            if prev and prev[-1] not in ".;:":
                return True
        return False

    @staticmethod
    def _is_heading_paragraph(para: str) -> bool:
        stripped = para.strip()
        if HEADING_ROMAN.match(stripped):
            return True
        if HEADING_NUMBERED.match(stripped):
            return len(stripped) < 100
        letters = re.sub(r"[^a-zA-ZáéíóúñÁÉÍÓÚÑ]", "", stripped)
        if len(stripped) < 140 and letters.isupper() and len(letters) > 8:
            return True
        return False

    @staticmethod
    def _is_bad_blank_paragraph(para: str, term: str) -> bool:
        """Evita partir encabezados romanos o en MAYÚSCULAS (ej. «II) ________ SOLEMNE…»)."""
        stripped = para.strip()
        is_section_heading = HEADING_ROMAN.match(stripped) or (
            len(stripped) < 140
            and len(re.sub(r"[^a-zA-ZáéíóúñÁÉÍÓÚÑ]", "", stripped)) > 8
            and re.sub(r"[^a-zA-ZáéíóúñÁÉÍÓÚÑ]", "", stripped).isupper()
        )
        if not is_section_heading:
            return False
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        if not pattern.search(para):
            return False
        words = re.findall(r"\w+", para, re.UNICODE)
        term_words = re.findall(r"\w+", term, re.UNICODE)
        return len(term_words) == 1 and len(words) > 2

    def _contains_term(self, text: str, term: str) -> bool:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        return bool(pattern.search(text))

    def _mask_term(self, text: str, term: str) -> str:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        return pattern.sub(BLANK, text, count=1)

    @staticmethod
    def check_answer(expected: str, given: str) -> dict:
        def norm(s: str) -> str:
            s = unicodedata.normalize("NFKC", s.lower().strip())
            return re.sub(r"[^\w\sáéíóúñ]", "", s)

        exp = norm(expected)
        got = norm(given)
        correct = exp == got or exp in got or got in exp
        return {"correct": correct, "expected": expected}
