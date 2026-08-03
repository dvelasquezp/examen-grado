"""Extractor OCR para PDFs de Flashcards con layout en grilla 2x4."""

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import fitz

from src.domain.ingestion.chunk import ExtractedBlock, ExtractedDocument
from src.infrastructure.documents.normalizer import sanitize_text


@dataclass
class FlashcardPair:
    title: str
    definition: str
    page_number: int
    card_index: int


class FlashcardsOcrExtractor:
    """
    Extrae pares concepto/definición desde Flashcards PDF.

    Layout por página (desde ~pág. 6):
    - Grilla 2 columnas x 4 filas
    - Celda izquierda: título (caja) + definición
    - Celda derecha: título grande (solo impresión; se ignora)
    """

    SKIP_PAGE_KEYWORDS = (
        "imprime el documento",
        "corta las flashcards",
        "dobla las tarjetas",
        "pegamento",
    )
    INDEX_PAGE_KEYWORDS = ("índice", "indice")

    ROWS = 4
    COLS = 2
    CONTENT_START_PAGE = 6
    OCR_SCALE = 2.5
    CELL_PADDING = 6

    def __init__(self, language: str = "spa", tessdata_dir: str | None = None):
        self.language = language
        self.tessdata_dir = tessdata_dir or self._default_tessdata_dir()

    @property
    def tesseract_available(self) -> bool:
        if self.tessdata_dir and Path(self.tessdata_dir, "spa.traineddata").exists():
            for candidate in (
                shutil.which("tesseract"),
                "/opt/homebrew/bin/tesseract",
                "/usr/local/bin/tesseract",
            ):
                if candidate and Path(candidate).exists():
                    return True
        return False

    def extract(self, filepath: Path) -> ExtractedDocument:
        if not self.tesseract_available:
            raise RuntimeError(
                "Las Flashcards PDF no tienen texto seleccionable. "
                "Instala Tesseract OCR: brew install tesseract tesseract-lang"
            )

        doc = fitz.open(filepath)
        blocks: list[ExtractedBlock] = []

        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            if page_number < self.CONTENT_START_PAGE:
                continue

            for pair in self._extract_page_pairs(doc[page_idx], page_number):
                blocks.append(
                    ExtractedBlock(
                        text=f"{pair.title}: {pair.definition}",
                        page_number=page_number,
                        block_type="paragraph",
                    )
                )

        page_count = len(doc)
        doc.close()
        return ExtractedDocument(blocks=blocks, page_count=page_count)

    def _extract_page_pairs(self, page: fitz.Page, page_number: int) -> list[FlashcardPair]:
        width = page.rect.width
        height = page.rect.height
        row_height = height / self.ROWS
        col_width = width / self.COLS

        pairs: list[FlashcardPair] = []
        for row in range(self.ROWS):
            rect = fitz.Rect(
                self.CELL_PADDING,
                row * row_height + self.CELL_PADDING,
                col_width - self.CELL_PADDING,
                (row + 1) * row_height - self.CELL_PADDING,
            )
            text = self._ocr_rect(page, rect)
            if not text.strip():
                continue
            if self._is_instruction_page(text) or self._is_index_page(text):
                continue
            parsed = self._parse_cell_text(text)
            if parsed:
                title, definition = parsed
                pairs.append(
                    FlashcardPair(
                        title=title,
                        definition=definition,
                        page_number=page_number,
                        card_index=row + 1,
                    )
                )
        return pairs

    def _ocr_rect(self, page: fitz.Page, rect: fitz.Rect) -> str:
        matrix = fitz.Matrix(self.OCR_SCALE, self.OCR_SCALE)
        pix = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
        # OCR sobre subpágina renderizada para evitar ruido de la columna derecha
        sub_doc = fitz.open(stream=pix.tobytes("png"), filetype="png")
        sub_page = sub_doc[0]
        textpage = sub_page.get_textpage_ocr(
            language=self.language,
            full=True,
            tessdata=self.tessdata_dir,
        )
        text = sanitize_text(textpage.extractText())
        sub_doc.close()
        return text

    def _parse_cell_text(self, text: str) -> tuple[str, str] | None:
        raw_lines = [sanitize_text(ln) for ln in text.splitlines()]
        lines = [ln for ln in raw_lines if ln and not self._is_noise_line(ln)]
        if len(lines) < 2:
            return None

        title_lines: list[str] = []
        definition_lines: list[str] = []
        idx = 0

        while idx < len(lines):
            line = self._normalize_title_line(lines[idx])
            if self._is_title_fragment(line):
                title_lines.append(line)
                idx += 1
                continue
            if title_lines:
                break
            idx += 1

        while idx < len(lines):
            definition_lines.append(lines[idx])
            idx += 1

        title = self._clean_title(" ".join(title_lines))
        definition = self._clean_definition(" ".join(definition_lines))

        if not title or not definition:
            return None
        if len(title) < 3 or len(definition) < 15:
            return None
        if not self._is_valid_title(title):
            return None
        return title, definition

    @staticmethod
    def _normalize_title_line(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = cleaned[1:-1].strip()
        return cleaned

    @staticmethod
    def _is_title_fragment(text: str) -> bool:
        cleaned = FlashcardsOcrExtractor._normalize_title_line(text)
        if not cleaned or FlashcardsOcrExtractor._is_noise_line(cleaned):
            return False
        if FlashcardsOcrExtractor._is_definition_start(cleaned):
            return False
        if re.search(r"[«»<>]{2,}", cleaned):
            return False
        if cleaned.endswith(",") and len(cleaned) <= 5:
            return False

        letters = re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", cleaned)
        if len(letters) < 4:
            return False

        words = cleaned.split()
        if len(words) > 8:
            return False

        upper_chars = sum(1 for c in letters if c.isupper())
        if cleaned.isupper() or upper_chars / max(len(letters), 1) >= 0.75:
            return True

        # Títulos tipo "Acto Jurídico (Vial)" con mayúscula inicial por palabra
        titled_words = sum(1 for w in words if w[:1].isupper())
        return titled_words >= max(2, len(words) - 1) and len(cleaned) <= 80

    @staticmethod
    def _is_definition_start(text: str) -> bool:
        stripped = text.strip()
        lowered = stripped.lower()
        if re.match(r"^[a-z]\)", lowered):
            return True
        if stripped[:1].islower() and not stripped.isupper():
            return True
        if re.match(
            r"^(acto|acuerdo|facultad|manifestaci[oó]n|falsa|falso|sanci[oó]n|m[aá]quinaci[oó]n)\b",
            lowered,
        ):
            words = stripped.split()
            titled_words = sum(1 for w in words if w[:1].isupper())
            if stripped.isupper() or (len(stripped) <= 60 and titled_words >= max(1, len(words) - 1)):
                return False
            return True
        return False

    @staticmethod
    def _is_noise_line(text: str) -> bool:
        cleaned = text.strip()
        if not cleaned:
            return True
        if len(cleaned) <= 2:
            return True
        if re.fullmatch(r"[\W_]+", cleaned):
            return True
        letters = re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", cleaned)
        return len(letters) <= 1

    @staticmethod
    def _clean_title(text: str) -> str:
        text = re.sub(r"\s+", " ", text.strip())
        text = re.sub(r"^\d+\.?\s*", "", text)
        text = re.sub(r"\bDELA\b", "DE LA", text)
        text = re.sub(r"\bDERECHO\b", "DERECHO", text)
        return text.strip(":-–—. ")

    @staticmethod
    def _clean_definition(text: str) -> str:
        text = re.sub(r"\s+", " ", text.strip())
        return text[:2000]

    @staticmethod
    def _is_valid_title(title: str) -> bool:
        if not title or not title[0].isupper():
            return False
        letters = re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ ]", "", title)
        if len(letters) < 3:
            return False
        if len(title.split()) > 12:
            return False
        lowered = title.lower()
        if re.search(r"^(acontecer|regular la|que se|manifestaci[oó]n de|eos)\b", lowered):
            return False
        if re.search(r"\b(una cosa|la negativa)\b", lowered):
            return False
        return True

    @classmethod
    def _is_instruction_page(cls, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in cls.SKIP_PAGE_KEYWORDS)

    @classmethod
    def _is_index_page(cls, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in cls.INDEX_PAGE_KEYWORDS)

    @staticmethod
    def _default_tessdata_dir() -> str | None:
        candidates = [
            os.environ.get("TESSDATA_PREFIX"),
            "/opt/homebrew/share/tessdata",
            "/usr/local/share/tessdata",
        ]
        for path in candidates:
            if path and Path(path, "spa.traineddata").exists():
                return path
        return None
