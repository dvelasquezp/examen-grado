"""Fábrica de extractores por extensión y tipo de documento."""

from pathlib import Path

from src.domain.catalog.enums import DocumentType
from src.domain.ingestion.chunk import ExtractedDocument
from src.infrastructure.documents.docx_extractor import DocxExtractor
from src.infrastructure.documents.flashcards_ocr_extractor import FlashcardsOcrExtractor
from src.infrastructure.documents.pdf_extractor import PdfExtractor


class DocumentExtractorFactory:
    def __init__(self):
        self._pdf = PdfExtractor()
        self._docx = DocxExtractor()
        self._flashcards_ocr = FlashcardsOcrExtractor()

    def extract(
        self,
        filepath: Path,
        *,
        document_type: DocumentType | None = None,
    ) -> ExtractedDocument:
        suffix = filepath.suffix.lower()
        if suffix == ".pdf" and document_type == DocumentType.FLASHCARDS:
            extracted = self._pdf.extract(filepath)
            if self._has_flashcard_content(extracted):
                return extracted
            return self._flashcards_ocr.extract(filepath)
        if suffix == ".pdf":
            return self._pdf.extract(filepath)
        if suffix == ".docx":
            return self._docx.extract(filepath)
        raise ValueError(f"Formato no soportado: {suffix}")

    @staticmethod
    def _has_flashcard_content(extracted: ExtractedDocument) -> bool:
        meaningful = 0
        for block in extracted.blocks:
            text = block.text.strip()
            if len(text) < 20:
                continue
            if "imprime el documento" in text.lower():
                continue
            if ":" in text or "\n" in text:
                meaningful += 1
        return meaningful >= 3
