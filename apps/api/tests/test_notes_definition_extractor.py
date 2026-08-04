"""Tests del extractor de definiciones desde apuntes."""

from uuid import uuid4

from src.infrastructure.knowledge.notes_definition_extractor import NotesDefinitionExtractor


def test_extrae_definicion_con_salto_de_linea_en_apunte():
    extractor = NotesDefinitionExtractor()
    text = (
        "4. La aceptación.\n\n"
        "Aceptación: AJ unilateral por el cual el destinatario de la oferta manifiesta su \n"
        "conformidad con ella.\n\n"
        "a) Clasificación de la aceptación."
    )
    results = extractor.extract_from_chunk(
        text,
        document_id=uuid4(),
        document_filename="(1) Acto Jurídico (v2023).pdf",
        chunk_id=uuid4(),
        page_number=20,
        area_name="Acto Jurídico",
    )

    assert len(results) == 1
    assert "su conformidad con ella" in results[0].definition


def test_extrae_definicion_explicita_desde_apunte():
    extractor = NotesDefinitionExtractor()
    text = (
        "4. La aceptación.\n\n"
        "Aceptación: AJ unilateral por el cual el destinatario de la oferta manifiesta "
        "su conformidad con ella.\n\n"
        "a) Clasificación de la aceptación."
    )
    results = extractor.extract_from_chunk(
        text,
        document_id=uuid4(),
        document_filename="(1) Acto Jurídico (v2023).pdf",
        chunk_id=uuid4(),
        page_number=20,
        area_name="Acto Jurídico",
    )

    assert len(results) == 1
    assert results[0].title == "Aceptación"
    assert "por el cual el destinatario de la oferta" in results[0].definition
    assert "su conformidad" in results[0].definition


def test_expande_abreviatura_aj():
    extractor = NotesDefinitionExtractor()
    normalized = extractor._normalize_definition(
        "AJ unilateral por el cual el destinatario de la oferta manifiesta su conformidad con ella"
    )
    assert normalized.startswith("Acto jurídico unilateral")


def test_detecta_definicion_apuntes_mas_completa_que_ocr():
    extractor = NotesDefinitionExtractor()
    ocr = "Acto jurídico unilateral por cual destinatario oferta manifiesta conformidad con ella."
    apunte = (
        "Acto jurídico unilateral por el cual el destinatario de la oferta manifiesta "
        "su conformidad con ella."
    )

    assert extractor.is_richer_definition(ocr, apunte)
    assert not extractor.is_richer_definition(apunte, ocr)


def test_no_reemplaza_definicion_sin_solapamiento():
    extractor = NotesDefinitionExtractor()
    current = "Bienes corporales e incorporales según el Código Civil."
    unrelated = "Acto jurídico unilateral por el cual el destinatario de la oferta manifiesta su conformidad con ella."

    assert not extractor.is_richer_definition(current, unrelated)
