"""Tests de generadores de juegos."""

import re

from src.application.study.fill_blank_generator import FillBlankGenerator
from src.application.study.graph_service import (
    build_matching_definition,
    expand_to_sentences,
    split_complete_sentences,
)
from src.application.study.logic_exercise_generator import LogicExerciseGenerator


def test_expand_to_sentences_full_stops():
    text = (
        "Es el acuerdo de voluntades. Produce efectos jurídicos. "
        "Debe cumplir requisitos de forma. Extra que no debería aparecer."
    )
    result = expand_to_sentences(text, max_sentences=2, max_chars=200)
    assert result.endswith(".")
    assert result[0].isupper()
    assert "acuerdo" in result
    assert "Extra" not in result
    assert "…" not in result


def test_split_rejects_mid_sentence_fragment():
    fragment = "ue el juez o el acreedor la autoricen, pero según al art. 453 CPC."
    sentences = split_complete_sentences(fragment)
    assert sentences == []


def test_split_accepts_embedded_sentence_in_chunk():
    chunk = (
        "…texto previo cortado. Disminución actual efectiva del patrimonio del acreedor "
        "como consecuencia de la infracción de una obligación."
    )
    sentences = split_complete_sentences(chunk)
    assert len(sentences) >= 1
    assert sentences[0][0].isupper()
    assert sentences[0].endswith(".")


def test_build_matching_definition_skips_bad_excerpt():
    canonical = (
        "Es un derecho real que grava un inmueble sin que deje de permanecer en poder del deudor. "
        "Asegura el cumplimiento de una obligación principal."
    )
    excerpt = "derecho prenda, constituido sobre inmuebles que no dejan por eso de permanecer en poder del deudor…"
    result = build_matching_definition(canonical, excerpt)
    assert result.startswith("Es un derecho")
    assert "…" not in result
    assert "derecho prenda, constituido" not in result.lower() or result[0].isupper()


def test_build_matching_definition_no_trailing_ellipsis():
    canonical = "Facultad que compete a los acreedores hereditarios y testamentarios a fin de que los bienes hereditarios no se confundan."
    excerpt = "Facultad que compete a los acreedores hereditarios y testamentarios a fin de que los bienes hereditarios no se…"
    result = build_matching_definition(canonical, excerpt)
    assert "…" not in result
    assert result.endswith(".")


def test_build_matching_definition_prefers_longer_excerpt():
    canonical = "Contrato."
    excerpt = (
        "El contrato es un acuerdo de voluntades entre dos o más personas. "
        "Genera obligaciones para las partes."
    )
    result = build_matching_definition(canonical, excerpt)
    assert "acuerdo" in result
    assert len(result) > len(canonical)


def test_fill_blank_check_exact():
    result = FillBlankGenerator.check_answer("Aceptación", "aceptación")
    assert result["correct"] is True


def test_fill_blank_check_partial():
    result = FillBlankGenerator.check_answer("Aceptación", "la aceptación")
    assert result["correct"] is True


def test_fill_blank_context_window():
    gen = FillBlankGenerator(None)  # type: ignore[arg-type]
    content = (
        "CAUSA: El matrimonio putativo produce los mismos efectos civiles que el válido "
        "respecto del cónyuge que, de buena fe y con justa causa de error, lo contrajo, "
        "si bien dejará de producir los efectos civiles desde que falte la buena fe. "
        "El error debe recaer en la identidad de la persona del otro cónyuge."
    )
    paragraphs = gen._paragraphs(content)
    idx = next(i for i, p in enumerate(paragraphs) if "error" in p.lower())
    window = gen._extract_from_paragraph(paragraphs, idx, "error")
    assert window is not None
    assert "CAUSA" in window
    assert "matrimonio" in window


def test_fill_blank_starts_at_paragraph_not_previous_section():
    gen = FillBlankGenerator(None)  # type: ignore[arg-type]
    content = (
        "Habilidad putativa del funcionario.\n\n"
        "CS ha fallado en ambos sentidos. Somarriva argumenta que no se comunica el vicio, "
        "en virtud del error común, facit ius. De otro modo sería necesario tener certeza "
        "de la legalidad del nombramiento del funcionario.\n\n"
        "II) TESTAMENTO SOLEMNE OTORGADO EN EL EXTRANJERO\n\n"
        "1. Testamento otorgado en el extranjero en conformidad a la ley extranjera. "
        "Art. 1027: 1) Debe otorgarse por escrito."
    )
    paragraphs = gen._paragraphs(content)
    idx = next(i for i, p in enumerate(paragraphs) if p.startswith("1. Testamento"))
    window = gen._extract_from_paragraph(paragraphs, idx, "Testamento")
    assert "Somarriva" not in window
    assert "II)" in window
    assert "1027" in window


def test_fill_blank_merges_soft_wrapped_lines():
    gen = FillBlankGenerator(None)  # type: ignore[arg-type]
    content = (
        "2. EL ERROR DE HECHO\n\n"
        "Las hipótesis de error constituyen una discrepancia entre lo querido y lo\n"
        "declarado.\n"
        "Sin embargo, en el error obstativo u obstáculo, no se produce esta discrepancia."
    )
    paragraphs = gen._paragraphs(content)
    assert any("lo declarado" in p for p in paragraphs)
    assert not any(re.search(r"\blo\s*$", p) for p in paragraphs)


def test_fill_blank_build_includes_full_sentence():
    gen = FillBlankGenerator(None)  # type: ignore[arg-type]
    content = (
        "2. EL ERROR DE HECHO\n\n"
        "Las hipótesis de error constituyen una discrepancia entre lo querido y lo\n"
        "declarado.\n"
        "Sin embargo, en el error obstativo u obstáculo, no se produce esta discrepancia."
    )
    paragraphs = gen._paragraphs(content)
    idx = next(i for i, p in enumerate(paragraphs) if "hipótesis" in p)
    window = gen._extract_from_paragraph(paragraphs, idx, "error")
    assert window is not None
    assert "lo declarado" in window
    assert "Sin embargo" in window


def test_fill_blank_skips_heading_word():
    gen = FillBlankGenerator(None)  # type: ignore[arg-type]
    content = (
        "II) TESTAMENTO SOLEMNE OTORGADO EN EL EXTRANJERO\n\n"
        "1. Testamento otorgado en el extranjero en conformidad a la ley extranjera."
    )
    paragraphs = gen._paragraphs(content)
    assert gen._is_bad_blank_paragraph(paragraphs[0], "TESTAMENTO") is True
    assert gen._is_bad_blank_paragraph(paragraphs[1], "Testamento") is False


def test_fill_blank_mask_term():
    gen = FillBlankGenerator(None)  # type: ignore[arg-type]
    masked = gen._mask_term(
        "aquella que se produce antes de la Aceptación de la oferta",
        "Aceptación",
    )
    assert "________" in masked
    assert "Aceptación" not in masked


def test_logic_check():
    assert LogicExerciseGenerator.check_answer("AND", "AND") is True
    assert LogicExerciseGenerator.check_answer("AND", "OR") is False


def test_logic_fallback_exercises():
    gen = LogicExerciseGenerator(None)  # type: ignore[arg-type]
    exercises = gen._fallback_exercises(3)
    assert len(exercises) == 3
    assert exercises[0]["context"]
    assert exercises[0]["explanation"]
    assert len(exercises[0]["options"]) >= 2
    assert all("label" in o and len(o["label"]) > 20 for o in exercises[0]["options"])


def test_logic_necessary_condition():
    gen = LogicExerciseGenerator(None)  # type: ignore[arg-type]
    pair = {
        "id_a": "1",
        "title_a": "Oferta",
        "id_b": "2",
        "title_b": "Contrato",
        "context": "La oferta es requisito previo al contrato.",
    }
    ex = gen._necessary_condition_exercise(pair)
    assert ex["correct_option"] == "IMPLIES_BA"
    assert "Oferta" in ex["question"]
    assert "Contrato" in ex["question"]
