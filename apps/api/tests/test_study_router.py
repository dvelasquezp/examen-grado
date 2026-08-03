"""Tests del router de estudio."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.study.oral_exam_service import OralExamService
from src.application.study.progress_service import ProgressService
from src.main import app


class _FakeResult:
    def scalar_one_or_none(self):
        return None


class _FakeSession:
    """Sesión mínima para ejercitar el cálculo sin base de datos."""

    def __init__(self):
        self.added = []

    async def execute(self, _query):
        return _FakeResult()

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("quality", [0, 3, 5])
async def test_primera_calificacion_de_una_tarjeta_nueva(quality: int):
    # Los valores por defecto del modelo sólo existen tras insertar, así que la
    # primera calificación debe partir de números y no de None.
    session = _FakeSession()
    prog = await ProgressService(session).record_review(uuid4(), quality)

    assert prog.interval_days >= 1
    assert prog.next_review_at is not None
    assert 0.0 <= prog.mastery_score <= 1.0


@pytest.mark.asyncio
async def test_progress_subject_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/subjects/no-existe/progress")
    assert response.status_code == 404


def test_oral_exam_evaluate_overlap():
    definition = "El contrato es un acuerdo de voluntades entre dos o más partes"
    answer = "Es un acuerdo de voluntades entre partes que crea obligaciones"
    result = OralExamService._evaluate(answer, definition)
    assert result["coverage"] > 0.3
    assert "score" in result
    assert result["feedback"]


def test_oral_exam_evaluate_empty():
    result = OralExamService._evaluate("   ", "definición")
    assert result["score"] == 0.0
