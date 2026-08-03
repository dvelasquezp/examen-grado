"""Catálogo: materias, documentos, tipos de fuente."""

from enum import StrEnum


class DocumentType(StrEnum):
    OFFICIAL_SYLLABUS = "OFFICIAL_SYLLABUS"
    FLASHCARDS = "FLASHCARDS"
    LECTURE_NOTES = "LECTURE_NOTES"
    EXAM_GUIDE = "EXAM_GUIDE"


class SourceRole(StrEnum):
    DOCTRINE = "DOCTRINE"
    EXAM_PATTERN_ONLY = "EXAM_PATTERN_ONLY"


class IngestionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
