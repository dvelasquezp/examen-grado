"""Tests del servicio de descubrimiento."""

from pathlib import Path

import pytest

from src.config.settings import Settings
from src.domain.catalog.discovery import SubjectDiscoveryService
from src.domain.catalog.enums import DocumentType, SourceRole


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        content_path=str(tmp_path),
        content_exclude_dirs="apps,node_modules,.git",
    )


@pytest.fixture
def sample_content(tmp_path: Path) -> Path:
    root = tmp_path
    (root / "Cedulario Examen de Grado.pdf").write_bytes(b"cedulario")
    civil = root / "Derecho Civil"
    civil.mkdir()
    (civil / "Flashcards-Digitales-Derecho-Civil.pdf").write_bytes(b"flashcards")
    (civil / "Guía Examen de Grado - Derecho Civil.docx").write_bytes(b"guia")
    apuntes = civil / "Apuntes"
    apuntes.mkdir()
    (apuntes / "(1) Acto Jurídico (v2023).pdf").write_bytes(b"apuntes1")
    (apuntes / "(2) Teoría de la Ley (v2023).pdf").write_bytes(b"apuntes2")
    return root


class TestSubjectDiscovery:
    def test_discovers_subjects(self, settings, sample_content):
        settings.content_path = str(sample_content)
        service = SubjectDiscoveryService(settings)
        result = service.discover()

        assert len(result.subjects) == 1
        assert result.subjects[0].name == "Derecho Civil"
        assert result.subjects[0].slug == "derecho-civil"

    def test_discovers_all_document_types(self, settings, sample_content):
        settings.content_path = str(sample_content)
        service = SubjectDiscoveryService(settings)
        result = service.discover()

        types = {d.document.document_type for d in result.documents}
        assert DocumentType.OFFICIAL_SYLLABUS in types
        assert DocumentType.FLASHCARDS in types
        assert DocumentType.LECTURE_NOTES in types
        assert DocumentType.EXAM_GUIDE in types

    def test_guia_is_exam_pattern_only(self, settings, sample_content):
        settings.content_path = str(sample_content)
        service = SubjectDiscoveryService(settings)
        result = service.discover()

        guia_docs = [d for d in result.documents if d.document.document_type == DocumentType.EXAM_GUIDE]
        assert len(guia_docs) == 1
        assert guia_docs[0].document.source_role == SourceRole.EXAM_PATTERN_ONLY

    def test_computes_file_hash(self, settings, sample_content):
        settings.content_path = str(sample_content)
        service = SubjectDiscoveryService(settings)
        result = service.discover()

        for doc in result.documents:
            assert len(doc.document.file_hash) == 64

    def test_skips_code_directories(self, settings, sample_content):
        (sample_content / "apps").mkdir()
        (sample_content / "apps" / "fake.pdf").write_bytes(b"should skip")
        settings.content_path = str(sample_content)
        service = SubjectDiscoveryService(settings)
        result = service.discover()

        filenames = [d.document.filename for d in result.documents]
        assert "fake.pdf" not in filenames

    def test_merges_derecho_civil_2_into_same_subject(self, settings, sample_content):
        civil2 = sample_content / "DERECHO CIVIL 2"
        (civil2 / "1. ACTO JURÍDICO").mkdir(parents=True)
        (civil2 / "MEMORIZADOR CIVIL.pdf").write_bytes(b"memo")
        (civil2 / "1. ACTO JURÍDICO" / "resumen.pdf").write_bytes(b"notes")
        settings.content_path = str(sample_content)
        service = SubjectDiscoveryService(settings)
        result = service.discover()

        assert len(result.subjects) == 1
        assert result.subjects[0].slug == "derecho-civil"
        filenames = {d.document.filename for d in result.documents}
        assert "MEMORIZADOR CIVIL.pdf" in filenames
        assert "resumen.pdf" in filenames
        civil2_docs = [
            d for d in result.documents if d.document.filepath.startswith("DERECHO CIVIL 2")
        ]
        assert all(d.subject and d.subject.slug == "derecho-civil" for d in civil2_docs)
