"""Empareja conceptos de flashcards con definiciones del MEMORIZADOR CIVIL.

El memorizador tiene texto nativo (sin OCR) y replica el mazo de flashcards, pero
los rótulos no siempre coinciden letra por letra («La oferta» frente a «OFERTA»).
Por eso se busca por título aproximado y sólo se acepta una definición si el
contenido concuerda con la tarjeta OCR: misma idea, con conectores completos.
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz

from src.infrastructure.knowledge.notes_definition_extractor import NotesDefinitionExtractor

LABEL_PREFIX = re.compile(r"^\d+\.\s*")
LETTER_PREFIX = re.compile(r"^[A-Z]\)\s*", re.IGNORECASE)
ARTICLE_PREFIX = re.compile(r"^(La|El|Los|Las)\s+", re.IGNORECASE)
ART_SUFFIX = re.compile(r"\s+Art\.?\s+\d+.*$", re.IGNORECASE)
PARENS_SUFFIX = re.compile(r"\s*\([^)]*\)\s*")

# Misma idea que la tarjeta OCR, pero exige solapamiento suficiente para evitar
# emparejar títulos rotos del OCR con entradas distintas del memorizador.
MIN_OVERLAP = 0.5
STRONG_OVERLAP = 0.65
CONTENT_ONLY_MIN = 0.55
CONTENT_ONLY_MARGIN = 0.08

# Conectores frecuentes pegados por OCR en rótulos en MAYÚSCULAS (p. ej. DETESTAMENTO).
GLUED_CAPS_SUFFIXES = (
    "TESTAMENTO",
    "HERENCIA",
    "SUCESION",
    "SUCESIÓN",
    "CONTRATO",
    "OBLIGACION",
    "OBLIGACIÓN",
    "CAPACIDAD",
    "COMPRAVENTA",
    "DONACION",
    "DONACIÓN",
    "HIPOTECA",
    "USUFRUCTO",
    "SERVIDUMBRE",
    "PROPIEDAD",
    "MATRIMONIO",
    "FILIACION",
    "FILIACIÓN",
    "PATRIA",
    "POTESTAD",
    "PRESCRIPCION",
    "PRESCRIPCIÓN",
    "NULIDAD",
    "RESCISION",
    "RESCISIÓN",
    "RESOLUCION",
    "RESOLUCIÓN",
    "POSESION",
    "POSESIÓN",
    "COMUNIDAD",
    "SOCIEDAD",
    "PERSONA",
    "BIENES",
    "DOMINIO",
    "USO",
)
GLUED_CAPS_CONNECTORS = ("DEL", "DE", "LOS", "LAS", "LA", "EL", "EN", "POR", "CON", "AL")

ENTRY_PATTERN = re.compile(
    r"(?:^|\n)\s*"
    r"(?P<label>[A-ZÁÉÍÓÚÑ0-9][^\n:]{1,100}?)\s*:\s*"
    r"(?P<def>.{15,600}?)\.",
    re.MULTILINE,
)


@dataclass(frozen=True)
class MemorizadorEntry:
    label: str
    definition: str


class MemorizadorMatcher:
    def __init__(self):
        self._extractor = NotesDefinitionExtractor()

    @staticmethod
    def find_pdf(content_root: Path) -> Path | None:
        """Localiza MEMORIZADOR CIVIL.pdf bajo la raíz de contenido."""
        root = content_root.resolve()
        patterns = ("*MEMORIZADOR*.pdf", "*Memorizador*.pdf", "*memorizador*.pdf")
        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(root.rglob(pattern))
            if root.parent != root:
                candidates.extend(root.parent.rglob(pattern))
        if not candidates:
            return None
        # Preferir el archivo cuyo nombre mencione explícitamente memorizador civil
        candidates.sort(
            key=lambda path: (
                "memorizador" not in path.name.lower(),
                len(path.name),
            )
        )
        return candidates[0]

    def load_entries(self, pdf_path: Path) -> list[MemorizadorEntry]:
        doc = fitz.open(pdf_path)
        try:
            text = "\n".join(page.get_text("text") for page in doc)
        finally:
            doc.close()
        prepared = self._extractor._prepare_content(text)
        entries: list[MemorizadorEntry] = []
        for match in ENTRY_PATTERN.finditer(prepared):
            label = self._clean_label(match.group("label"))
            definition = self._extractor._normalize_definition(match.group("def"))
            if len(label) >= 3 and len(definition) >= 20:
                entries.append(MemorizadorEntry(label=label, definition=definition))
        return entries

    def match(
        self,
        concept_title: str,
        flashcard_definition: str | None,
        entries: list[MemorizadorEntry],
    ) -> MemorizadorEntry | None:
        if not flashcard_definition or len(flashcard_definition.strip()) < 15:
            return None

        repaired_title = self.repair_ocr_title(concept_title)

        best: MemorizadorEntry | None = None
        best_overlap = 0.0
        for entry in entries:
            if not self._labels_match(repaired_title, entry.label):
                continue
            overlap = self._extractor.content_overlap(flashcard_definition, entry.definition)
            if overlap > best_overlap:
                best_overlap = overlap
                best = entry

        if best and self._is_concordant(flashcard_definition, best.definition, best_overlap):
            return best

        return self._match_by_content(flashcard_definition, entries)

    def canonical_title(self, label: str) -> str:
        """Título legible para corregir rótulos OCR rotos (p. ej. DETESTAMENTO)."""
        cleaned = self._clean_label(label)
        cleaned = ART_SUFFIX.sub("", cleaned).strip()
        return self.repair_ocr_title(cleaned).upper()

    @classmethod
    def repair_ocr_title(cls, text: str) -> str:
        """Separa conectores pegados por OCR en rótulos; no altera definiciones."""
        if not text:
            return text
        tokens = text.split()
        fixed = [cls._repair_caps_token(token) for token in tokens]
        return re.sub(r"\s+", " ", " ".join(fixed)).strip()

    @classmethod
    def _repair_caps_token(cls, token: str) -> str:
        if len(token) < 6:
            return token

        letters = sum(ch.isalpha() for ch in token)
        uppers = sum(ch.isupper() for ch in token)
        if letters == 0 or uppers / letters < 0.7:
            return token

        folded = unicodedata.normalize("NFKD", token.upper())
        plain = "".join(ch for ch in folded if not unicodedata.combining(ch))

        for suffix in GLUED_CAPS_SUFFIXES:
            suffix_plain = "".join(
                ch for ch in unicodedata.normalize("NFKD", suffix.upper())
                if not unicodedata.combining(ch)
            )
            for conn in GLUED_CAPS_CONNECTORS:
                glued = conn + suffix_plain
                if plain == glued:
                    return f"{conn} {suffix}"

        return token

    def _match_by_content(
        self,
        flashcard_definition: str,
        entries: list[MemorizadorEntry],
    ) -> MemorizadorEntry | None:
        """Respaldo cuando el título OCR está tan roto que no empareja por rótulo."""
        scored: list[tuple[float, MemorizadorEntry]] = []
        for entry in entries:
            overlap = self._extractor.content_overlap(flashcard_definition, entry.definition)
            if overlap >= CONTENT_ONLY_MIN:
                scored.append((overlap, entry))

        if not scored:
            return None

        scored.sort(key=lambda item: item[0], reverse=True)
        best_overlap, best = scored[0]
        if len(scored) > 1 and best_overlap - scored[1][0] < CONTENT_ONLY_MARGIN:
            return None

        if not self._is_concordant(flashcard_definition, best.definition, best_overlap):
            return None

        flash_fw = self._extractor.function_word_count(flashcard_definition)
        memo_fw = self._extractor.function_word_count(best.definition)
        if memo_fw < flash_fw:
            return None

        return best

    def _is_concordant(
        self, flashcard_definition: str, memorizador_definition: str, overlap: float
    ) -> bool:
        if overlap < MIN_OVERLAP:
            return False
        if overlap >= STRONG_OVERLAP:
            return True
        flash_fw = self._extractor.function_word_count(flashcard_definition)
        memo_fw = self._extractor.function_word_count(memorizador_definition)
        return memo_fw >= flash_fw + 1

    def _labels_match(self, concept_title: str, label: str) -> bool:
        concept = self._normalize_label(self.repair_ocr_title(concept_title))
        candidate = self._normalize_label(self.repair_ocr_title(label))
        if not concept or not candidate:
            return False
        if concept == candidate:
            return True

        concept_base = PARENS_SUFFIX.sub("", concept).strip()
        candidate_base = PARENS_SUFFIX.sub("", candidate).strip()
        if concept_base == candidate_base:
            return True

        shorter, longer = sorted((concept_base, candidate_base), key=len)
        if len(shorter) < 5:
            return False
        if shorter not in longer:
            return False
        return len(shorter) / len(longer) >= 0.6

    @staticmethod
    def _clean_label(text: str) -> str:
        cleaned = LABEL_PREFIX.sub("", text.strip())
        cleaned = LETTER_PREFIX.sub("", cleaned)
        cleaned = ARTICLE_PREFIX.sub("", cleaned)
        cleaned = ART_SUFFIX.sub("", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _normalize_label(text: str) -> str:
        folded = unicodedata.normalize("NFKD", text.strip().lower())
        return "".join(ch for ch in folded if not unicodedata.combining(ch))
