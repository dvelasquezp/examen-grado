"""Clasificador de documentos basado en convenciones de ruta."""

import fnmatch
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from src.domain.catalog.enums import DocumentType, SourceRole


@dataclass(frozen=True)
class ClassificationRule:
    pattern: str
    document_type: DocumentType
    source_role: SourceRole
    is_global: bool = False


RULES: list[ClassificationRule] = [
    ClassificationRule("Cedulario*.pdf", DocumentType.OFFICIAL_SYLLABUS, SourceRole.DOCTRINE, is_global=True),
    ClassificationRule("**/Flashcards*.pdf", DocumentType.FLASHCARDS, SourceRole.DOCTRINE),
    ClassificationRule("**/MEMORIZADOR*.pdf", DocumentType.FLASHCARDS, SourceRole.DOCTRINE),
    ClassificationRule("**/Memorizador*.pdf", DocumentType.FLASHCARDS, SourceRole.DOCTRINE),
    ClassificationRule("**/Apuntes/*.pdf", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    ClassificationRule("**/Guía*.docx", DocumentType.EXAM_GUIDE, SourceRole.EXAM_PATTERN_ONLY),
    ClassificationRule("**/Guia*.docx", DocumentType.EXAM_GUIDE, SourceRole.EXAM_PATTERN_ONLY),
    # Material doctrinal adicional (DERECHO CIVIL 2 y similares)
    ClassificationRule("**/Artículos*.pdf", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    ClassificationRule("**/Articulos*.pdf", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    ClassificationRule("**/Artículos*.docx", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    ClassificationRule("**/Articulos*.docx", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    ClassificationRule("**/Cuadros*.pdf", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    ClassificationRule("**/Pendientes*.docx", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    ClassificationRule("**/Pendientes*.pdf", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    # Catch-all: PDFs/DOCX doctrinales dentro de carpetas de materia
    ClassificationRule("**/*.pdf", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
    ClassificationRule("**/*.docx", DocumentType.LECTURE_NOTES, SourceRole.DOCTRINE),
]


class DocumentClassifier:
    """Clasifica documentos según ubicación y nombre de archivo."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

    def classify(self, filepath: Path, content_root: Path) -> tuple[DocumentType, SourceRole, bool] | None:
        try:
            relative = filepath.relative_to(content_root)
        except ValueError:
            return None

        if filepath.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return None

        relative_str = str(relative)
        normalized_name = self._normalize(filepath.name)
        normalized_relative = self._normalize(relative_str)

        for rule in RULES:
            pattern = self._normalize(rule.pattern)
            name_pattern = pattern.split("/")[-1]
            if fnmatch.fnmatch(normalized_relative, pattern) or fnmatch.fnmatch(normalized_name, name_pattern):
                return rule.document_type, rule.source_role, rule.is_global

        guia_pattern = re.compile(r"gu[ií]a.*examen.*grado", re.IGNORECASE)
        if filepath.suffix.lower() == ".docx" and guia_pattern.search(normalized_name):
            return DocumentType.EXAM_GUIDE, SourceRole.EXAM_PATTERN_ONLY, False

        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return unicodedata.normalize("NFC", text)

    def is_supported(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in self.SUPPORTED_EXTENSIONS
