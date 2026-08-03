"""Tests de las áreas del temario y de la segmentación del mazo de flashcards."""

from uuid import uuid4

import pytest

from src.application.knowledge.classify_areas import ClassifyAreasUseCase
from src.domain.knowledge.area import SubjectArea, parse_area


@pytest.mark.parametrize(
    ("filename", "order", "name"),
    [
        ("(4) Bienes (v06-2025).pdf", 4, "Bienes"),
        ("(10) Sucesorio (v2023).pdf", 10, "Sucesorio"),
        ("(9) Familia (01.2025).pdf", 9, "Familia"),
        ("(1) Acto Jurídico (v2023) .pdf", 1, "Acto Jurídico"),
        ("(8) REX (v2024).pdf", 8, "REX"),
        (
            "(2) Teoría de la Ley e Introducción al Derecho Civil (v2023).pdf",
            2,
            "Teoría de la Ley e Introducción al Derecho Civil",
        ),
    ],
)
def test_parse_area_extrae_orden_y_nombre(filename: str, order: int, name: str):
    area = parse_area(filename)
    assert area == SubjectArea(order=order, name=name)


def test_parse_area_normaliza_tildes_descompuestas():
    # Los PDF suelen traer las tildes en NFD.
    area = parse_area("(1) Acto Juri\u0301dico (v2023).pdf")
    assert area is not None
    assert area.name == "Acto Jurídico"


@pytest.mark.parametrize(
    "filename",
    ["Flashcards-Digitales-Derecho-Civil.pdf", "Guía Examen de Grado.docx", "(3).pdf"],
)
def test_parse_area_ignora_nombres_sin_patron(filename: str):
    assert parse_area(filename) is None


def _segment(evidence_by_card: list[dict[SubjectArea, float]]) -> list[SubjectArea]:
    ids = [uuid4() for _ in evidence_by_card]
    evidence = dict(zip(ids, evidence_by_card))
    areas = sorted({area for shares in evidence_by_card for area in shares}, key=lambda a: a.order)
    assignments = ClassifyAreasUseCase.__new__(ClassifyAreasUseCase)._segment(ids, evidence, areas)
    return [assignments[card_id] for card_id in ids]


def test_segmentacion_mantiene_tarjeta_dudosa_en_su_bloque():
    contratos = SubjectArea(order=7, name="Contratos")
    obligaciones = SubjectArea(order=5, name="Obligaciones")

    # La tercera tarjeta se inclina apenas hacia Obligaciones, pero está rodeada
    # de Contratos: abrir un bloque de una sola tarjeta no compensa.
    resultado = _segment(
        [
            {contratos: 0.9},
            {contratos: 0.8},
            {obligaciones: 0.55, contratos: 0.45},
            {contratos: 0.8},
            {contratos: 0.9},
        ]
    )
    assert resultado == [contratos] * 5


def test_segmentacion_cambia_de_area_cuando_varias_tarjetas_lo_respaldan():
    contratos = SubjectArea(order=7, name="Contratos")
    obligaciones = SubjectArea(order=5, name="Obligaciones")

    resultado = _segment(
        [
            {contratos: 0.9},
            {contratos: 0.9},
            {obligaciones: 0.8},
            {obligaciones: 0.9},
            {obligaciones: 0.9},
        ]
    )
    assert resultado == [contratos, contratos, obligaciones, obligaciones, obligaciones]


def test_segmentacion_asigna_tarjetas_sin_evidencia_al_bloque_vecino():
    # Los títulos dañados por OCR no se enlazan con ningún apunte.
    familia = SubjectArea(order=9, name="Familia")

    resultado = _segment([{familia: 0.9}, {}, {}, {familia: 0.9}])
    assert resultado == [familia] * 4
