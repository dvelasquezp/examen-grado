"""Tests del extractor OCR de flashcards."""

from src.infrastructure.documents.extractor_factory import DocumentExtractorFactory
from src.infrastructure.documents.flashcards_ocr_extractor import FlashcardsOcrExtractor


def test_skip_instruction_page():
    extractor = FlashcardsOcrExtractor(tessdata_dir="/opt/homebrew/share/tessdata")
    assert extractor._is_instruction_page(
        "Imprime el documento en tamaño carta, sin márgenes"
    )
    assert not extractor._is_instruction_page("Acto Jurídico: Manifestación de voluntad")


def test_parse_voluntad_cell():
    extractor = FlashcardsOcrExtractor(tessdata_dir="/opt/homebrew/share/tessdata")
    text = (
        "EOS,\n(\nVOLUNTAD\n)\nNo\nY\n"
        "a) Facultad de decidir y ordenar libremente\n"
        "la propia conducta. b) El querer interno de\nUna persona.\n"
    )
    parsed = extractor._parse_cell_text(text)
    assert parsed is not None
    title, definition = parsed
    assert title == "VOLUNTAD"
    assert "Facultad de decidir" in definition


def test_parse_acto_juridico_title_not_definition():
    extractor = FlashcardsOcrExtractor(tessdata_dir="/opt/homebrew/share/tessdata")
    assert not extractor._is_definition_start("ACTO JURÍDICO (VIAL)")
    text = (
        "ACTO JURÍDICO (VIAL)\n"
        "Manifestación de voluntad que persigue la creación, modificación o extinción "
        "de derechos y obligaciones.\n"
    )
    parsed = extractor._parse_cell_text(text)
    assert parsed is not None
    assert parsed[0] == "ACTO JURÍDICO (VIAL)"


def test_factory_detects_missing_flashcard_text():
    from src.domain.ingestion.chunk import ExtractedBlock, ExtractedDocument

    factory = DocumentExtractorFactory()
    extracted = ExtractedDocument(
        blocks=[
            ExtractedBlock(
                text="Imprime el documento en tamaño carta",
                page_number=2,
                block_type="paragraph",
            )
        ],
        page_count=51,
    )
    assert not factory._has_flashcard_content(extracted)
