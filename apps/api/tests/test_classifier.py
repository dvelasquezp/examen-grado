"""Tests del clasificador de documentos."""

from pathlib import Path

import pytest

from src.domain.catalog.classifier import DocumentClassifier
from src.domain.catalog.enums import DocumentType, SourceRole


@pytest.fixture
def classifier():
    return DocumentClassifier()


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    root.mkdir()
    return root


class TestDocumentClassifier:
    def test_classify_cedulario(self, classifier, content_root):
        ced = content_root / "Cedulario Examen de Grado.pdf"
        ced.touch()
        result = classifier.classify(ced, content_root)
        assert result is not None
        doc_type, source_role, is_global = result
        assert doc_type == DocumentType.OFFICIAL_SYLLABUS
        assert source_role == SourceRole.DOCTRINE
        assert is_global is True

    def test_classify_flashcards(self, classifier, content_root):
        civil = content_root / "Derecho Civil"
        civil.mkdir()
        fc = civil / "Flashcards-Digitales-Derecho-Civil.pdf"
        fc.touch()
        result = classifier.classify(fc, content_root)
        assert result is not None
        doc_type, source_role, _ = result
        assert doc_type == DocumentType.FLASHCARDS
        assert source_role == SourceRole.DOCTRINE

    def test_classify_apuntes(self, classifier, content_root):
        apuntes = content_root / "Derecho Civil" / "Apuntes"
        apuntes.mkdir(parents=True)
        pdf = apuntes / "(1) Acto Jurídico (v2023).pdf"
        pdf.touch()
        result = classifier.classify(pdf, content_root)
        assert result is not None
        doc_type, source_role, _ = result
        assert doc_type == DocumentType.LECTURE_NOTES
        assert source_role == SourceRole.DOCTRINE

    def test_classify_guia(self, classifier, content_root):
        civil = content_root / "Derecho Civil"
        civil.mkdir()
        guia = civil / "Guía Examen de Grado - Derecho Civil.docx"
        guia.touch()
        result = classifier.classify(guia, content_root)
        assert result is not None
        doc_type, source_role, _ = result
        assert doc_type == DocumentType.EXAM_GUIDE
        assert source_role == SourceRole.EXAM_PATTERN_ONLY

    def test_unsupported_extension(self, classifier, content_root):
        f = content_root / "readme.txt"
        f.touch()
        assert classifier.classify(f, content_root) is None

    def test_guia_never_doctrine(self, classifier, content_root):
        civil = content_root / "Derecho Civil"
        civil.mkdir()
        guia = civil / "Guía Examen de Grado - Derecho Civil.docx"
        guia.touch()
        result = classifier.classify(guia, content_root)
        _, source_role, _ = result  # type: ignore[misc]
        assert source_role != SourceRole.DOCTRINE
