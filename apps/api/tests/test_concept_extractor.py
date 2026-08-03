"""Tests del extractor de conceptos."""

from uuid import uuid4

from src.domain.catalog.enums import DocumentType, SourceRole
from src.infrastructure.knowledge.rule_extractor import RuleBasedConceptExtractor


def test_extract_flashcard_inline():
    extractor = RuleBasedConceptExtractor()
    content = "Acto Jurídico: Manifestación de voluntad destinada a crear, modificar o extinguir derechos."
    results = extractor.extract_from_chunk(
        content,
        document_id=uuid4(),
        document_filename="Flashcards.pdf",
        document_type=DocumentType.FLASHCARDS,
        source_role=SourceRole.DOCTRINE,
        chunk_id=uuid4(),
        page_start=1,
        chapter=None,
        section=None,
    )
    assert len(results) >= 1
    assert "Acto" in results[0].title
    assert results[0].confidence >= 0.85


def test_skip_exam_guide():
    extractor = RuleBasedConceptExtractor()
    results = extractor.extract_from_chunk(
        "Pregunta de examen oral sobre nulidad",
        document_id=uuid4(),
        document_filename="Guia.docx",
        document_type=DocumentType.EXAM_GUIDE,
        source_role=SourceRole.EXAM_PATTERN_ONLY,
        chunk_id=uuid4(),
        page_start=1,
        chapter=None,
        section=None,
    )
    assert results == []


def test_skip_lecture_notes():
    extractor = RuleBasedConceptExtractor()
    content = (
        "Se entiende por prescripción la forma de adquirir las cosas ajenas o de extinguir "
        "las acciones y derechos ajenos, mediante la no accionar durante cierto lapso de tiempo."
    )
    results = extractor.extract_from_chunk(
        content,
        document_id=uuid4(),
        document_filename="Apuntes.pdf",
        document_type=DocumentType.LECTURE_NOTES,
        source_role=SourceRole.DOCTRINE,
        chunk_id=uuid4(),
        page_start=45,
        chapter="Obligaciones",
        section=None,
    )
    assert results == []
