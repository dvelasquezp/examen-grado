"""Extrae definiciones explícitas desde apuntes (texto nativo del PDF).

Los apuntes definen conceptos con el patrón «Aceptación: AJ unilateral por el
cual el destinatario de la oferta…». Ese texto conserva artículos y
preposiciones que el OCR de las flashcards suele perder.
"""

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID

# Apuntes: «Título: definición.» antes de un apartado o salto de línea.
EXPLICIT_DEFINITION = re.compile(
    r"(?:^|\n)\s*"
    r"(?P<title>[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s\-\"\"']{2,80}?)\s*:\s*"
    r"(?P<def>[^\n]{20,800}?)\.",
    re.MULTILINE,
)

SKIP_TITLE = re.compile(
    r"^(artículo|art\.|ej\.|ejemplo|inc\.|literal|nota|capítulo|sección|\d+\.)",
    re.IGNORECASE,
)

ABBREVIATIONS = (
    (re.compile(r"\bAJ\b"), "Acto jurídico"),
    (re.compile(r"\bActos Jurídicos\b", re.IGNORECASE), "Acto jurídico"),
)

FUNCTION_WORDS = frozenset(
    {
        "el",
        "la",
        "los",
        "las",
        "de",
        "del",
        "al",
        "a",
        "en",
        "su",
        "sus",
        "un",
        "una",
        "por",
        "que",
        "se",
        "lo",
        "le",
        "con",
        "cual",
        "ella",
        "ello",
    }
)


@dataclass(frozen=True)
class NotesDefinition:
    title: str
    definition: str
    document_id: UUID
    document_filename: str
    chunk_id: UUID
    page_number: int | None
    area_name: str | None = None


class NotesDefinitionExtractor:
    def extract_from_chunk(
        self,
        content: str,
        *,
        document_id: UUID,
        document_filename: str,
        chunk_id: UUID,
        page_number: int | None,
        area_name: str | None = None,
    ) -> list[NotesDefinition]:
        prepared = self._prepare_content(content)
        results: list[NotesDefinition] = []
        for match in EXPLICIT_DEFINITION.finditer(prepared):
            title = self._clean_title(match.group("title"))
            definition = self._normalize_definition(match.group("def"))
            if not self._is_valid(title, definition):
                continue
            results.append(
                NotesDefinition(
                    title=title,
                    definition=definition,
                    document_id=document_id,
                    document_filename=document_filename,
                    chunk_id=chunk_id,
                    page_number=page_number,
                    area_name=area_name,
                )
            )
        return results

    @staticmethod
    def normalize_title(title: str) -> str:
        folded = unicodedata.normalize("NFKD", title.strip().lower())
        return "".join(ch for ch in folded if not unicodedata.combining(ch))

    @staticmethod
    def titles_match(left: str, right: str) -> bool:
        return NotesDefinitionExtractor.normalize_title(left) == NotesDefinitionExtractor.normalize_title(
            right
        )

    @staticmethod
    def function_word_count(text: str) -> int:
        return sum(1 for word in re.findall(r"[a-záéíóúñ]+", text.lower()) if word in FUNCTION_WORDS)

    @staticmethod
    def content_tokens(text: str) -> set[str]:
        return {
            word
            for word in re.findall(r"[a-záéíóúñ]{4,}", text.lower())
            if word not in FUNCTION_WORDS
        }

    @classmethod
    def content_overlap(cls, left: str, right: str) -> float:
        left_tokens = cls.content_tokens(left)
        right_tokens = cls.content_tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    @classmethod
    def is_richer_definition(cls, current: str | None, candidate: str) -> bool:
        """True si el candidato de apuntes mejora una definición OCR mutilada."""
        if not candidate.strip():
            return False
        if not current or not current.strip():
            return True

        current = current.strip()
        candidate = candidate.strip()
        if candidate.lower() == current.lower():
            return False

        overlap = cls.content_overlap(current, candidate)
        if overlap < 0.45:
            return False

        current_fw = cls.function_word_count(current)
        candidate_fw = cls.function_word_count(candidate)
        if candidate_fw >= current_fw + 2:
            return True

        return len(candidate) >= len(current) * 1.1 and overlap >= 0.55

    @staticmethod
    def _prepare_content(content: str) -> str:
        # Los PDF parten frases en varias líneas; unir antes de buscar «Título: …».
        return re.sub(r"(?<=[^\n])\n(?=[a-záéíóúñ\"'])", " ", content)

    @staticmethod
    def _clean_title(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip())[:120]

    @classmethod
    def _normalize_definition(cls, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text.strip())
        for pattern, replacement in ABBREVIATIONS:
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned[:2000]

    @staticmethod
    def _is_valid(title: str, definition: str) -> bool:
        if not title or not definition:
            return False
        if len(title) < 3 or len(definition) < 20:
            return False
        if SKIP_TITLE.match(title):
            return False
        if len(title.split()) > 12:
            return False
        if title.lower() == definition.lower()[: len(title)].lower():
            return False
        return True
