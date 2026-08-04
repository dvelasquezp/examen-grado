"""Tests del emparejamiento con MEMORIZADOR CIVIL."""

from pathlib import Path

from src.infrastructure.knowledge.memorizador_matcher import MemorizadorMatcher

MEMORIZADOR = (
    Path(__file__).resolve().parents[3]
    / "DERECHO CIVIL 2"
    / "MEMORIZADOR CIVIL.pdf"
)


def test_labels_match_oferta_y_la_oferta():
    matcher = MemorizadorMatcher()
    assert matcher._labels_match("OFERTA", "La oferta")
    assert matcher._labels_match("ACEPTACIÓN", "Aceptación")


def test_labels_rechazan_titulos_ocr_rotos():
    matcher = MemorizadorMatcher()
    assert not matcher._labels_match("APERTURA DE", "Apertura de la sucesión testamento")


def test_concordancia_aceptacion():
    matcher = MemorizadorMatcher()
    ocr = "Acto jurídico unilateral por cual destinatario oferta manifiesta conformidad con ella."
    memo = (
        "Acto jurídico unilateral por el cual el destinatario de la oferta manifiesta "
        "su conformidad con ella."
    )
    assert matcher._is_concordant(ocr, memo, matcher._extractor.content_overlap(ocr, memo))


def test_match_end_to_end_aceptacion():
    if not MEMORIZADOR.exists():
        return
    matcher = MemorizadorMatcher()
    entries = matcher.load_entries(MEMORIZADOR)
    ocr = "Acto jurídico unilateral por cual destinatario oferta manifiesta conformidad con ella."
    result = matcher.match("ACEPTACIÓN", ocr, entries)
    assert result is not None
    assert "por el cual el destinatario de la oferta" in result.definition
    assert "su conformidad" in result.definition


def test_no_match_si_contenido_no_concuerda():
    from src.infrastructure.knowledge.memorizador_matcher import MemorizadorEntry

    matcher = MemorizadorMatcher()
    entries = [
        MemorizadorEntry(
            label="Bienes",
            definition="Cosas corporales e incorporales según el Código Civil.",
        )
    ]
    ocr = "Acto jurídico unilateral por cual destinatario oferta manifiesta conformidad con ella."
    assert matcher.match("ACEPTACIÓN", ocr, entries) is None


def test_repair_ocr_title_detestamento():
    matcher = MemorizadorMatcher()
    assert matcher.repair_ocr_title("ACCIÓN DE REFORMA DETESTAMENTO") == (
        "ACCIÓN DE REFORMA DE TESTAMENTO"
    )


def test_repair_ocr_title_no_rompe_palabras_normales():
    matcher = MemorizadorMatcher()
    assert matcher.repair_ocr_title("ACEPTACIÓN") == "ACEPTACIÓN"
    assert matcher.repair_ocr_title("OFERTA") == "OFERTA"


def test_labels_match_reforma_con_titulo_ocr_roto():
    matcher = MemorizadorMatcher()
    assert matcher._labels_match(
        "ACCIÓN DE REFORMA DETESTAMENTO",
        "ACCION DE REFORMA DE TESTAMENTO",
    )


def test_match_reforma_testamento_por_contenido():
    if not MEMORIZADOR.exists():
        return
    matcher = MemorizadorMatcher()
    entries = matcher.load_entries(MEMORIZADOR)
    ocr = (
        "Aquella que correspondea los legitimarios O a sus herederos, en caso de que "
        "testador les haya respetado las legítimas mejores, según los casos, para pedir "
        "que se modifique el testamento en todo lo que perjudique dichas asignaciones."
    )
    result = matcher.match("ACCIÓN DE REFORMA DETESTAMENTO", ocr, entries)
    assert result is not None
    assert "no les haya respetado" in result.definition
    assert "el testador" in result.definition
