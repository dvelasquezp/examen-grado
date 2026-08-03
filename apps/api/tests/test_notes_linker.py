"""Tests del vinculador Apuntes → conceptos."""

from uuid import uuid4

from src.domain.knowledge.concept import Concept
from src.infrastructure.knowledge.notes_linker import NotesConceptLinker


def _concept(title: str) -> Concept:
    return Concept(
        id=uuid4(),
        subject_id=uuid4(),
        slug=title.lower().replace(" ", "-"),
        title=title,
        definition=f"Definición de {title}",
    )


def test_link_notes_by_title_mention():
    linker = NotesConceptLinker()
    acto = _concept("Acto Jurídico")
    nulidad = _concept("Nulidad")

    chunks = [
        (
            "El Acto Jurídico requiere capacidad y objeto lícito. "
            "La nulidad absoluta sanciona vicios graves.",
            uuid4(),
            uuid4(),
            "Apuntes-Contrato.pdf",
            12,
        )
    ]

    links = linker.find_links([acto, nulidad], chunks)
    titles = {link.concept_title for link in links}

    assert "Acto Jurídico" in titles
    assert "Nulidad" in titles
    assert all(link.match_type == "TITLE_MENTION" for link in links)
    assert all(link.relevance_score >= 0.75 for link in links)


def test_link_with_extra_whitespace_in_chunk():
    linker = NotesConceptLinker()
    concept = _concept("Acto Jurídico")
    chunks = [
        (
            "El   Acto   Jurídico   requiere capacidad.",
            uuid4(),
            uuid4(),
            "Apuntes.pdf",
            3,
        )
    ]
    links = linker.find_links([concept], chunks)
    assert len(links) == 1
    assert links[0].concept_title == "Acto Jurídico"


def test_skip_lecture_notes_in_extractor():
    from src.domain.catalog.enums import DocumentType, SourceRole
    from src.infrastructure.knowledge.rule_extractor import RuleBasedConceptExtractor

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
