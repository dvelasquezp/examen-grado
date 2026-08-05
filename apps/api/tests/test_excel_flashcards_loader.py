"""Tests del cargador de flashcards Excel."""

from pathlib import Path

from src.infrastructure.knowledge.excel_flashcards_loader import ExcelFlashcardsLoader

EXCEL = Path(__file__).resolve().parents[3] / "Flashcards_Derecho_Civil.xlsx"


def test_load_excel_flashcards():
    if not EXCEL.exists():
        return
    cards = ExcelFlashcardsLoader().load_path(EXCEL)
    assert len(cards) >= 150
    by_title = {c.title.lower(): c for c in cards}
    assert "aceptación" in by_title
    assert "destinatario de la oferta" in by_title["aceptación"].definition.lower()
    assert "el" in by_title["aceptación"].definition.lower()


def test_oferta_tiene_conectores():
    if not EXCEL.exists():
        return
    cards = ExcelFlashcardsLoader().load_path(EXCEL)
    oferta = next(c for c in cards if c.title.lower() == "oferta")
    assert "por el cual" in oferta.definition.lower()
