"""Tests del router de estudio."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.study.oral_exam_service import OralExamService
from src.main import app


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
