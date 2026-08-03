"""Simulacro oral (texto, evaluación heurística)."""

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.study.question_generator import QuestionGenerator
from src.infrastructure.persistence.postgres.knowledge_models import ConceptModel
from src.infrastructure.persistence.postgres.study_models import OralExamSessionModel


class OralExamService:
    MAX_QUESTIONS = 5

    def __init__(self, session: AsyncSession):
        self.session = session
        self.question_gen = QuestionGenerator(session)

    async def start_session(self, subject_id: UUID) -> dict:
        await self.question_gen.ensure_questions_for_subject(subject_id)
        session = OralExamSessionModel(subject_id=subject_id, status="active", transcript=[])
        self.session.add(session)
        await self.session.flush()
        question = await self._next_question(session)
        return {"session_id": session.id, **question}

    async def submit_answer(self, session_id: UUID, answer: str) -> dict:
        session = await self.session.get(OralExamSessionModel, session_id)
        if not session or session.status != "active":
            raise ValueError("Sesión no encontrada o ya finalizada")

        concept = await self.session.get(ConceptModel, session.current_concept_id)
        evaluation = self._evaluate(answer, concept.definition if concept else "")

        transcript = list(session.transcript or [])
        transcript.append(
            {
                "concept_id": str(session.current_concept_id),
                "concept_title": concept.title if concept else "",
                "answer": answer,
                "evaluation": evaluation,
                "asked_at": datetime.now(UTC).isoformat(),
            }
        )
        session.transcript = transcript
        session.questions_asked += 1

        if session.questions_asked >= self.MAX_QUESTIONS:
            session.status = "completed"
            session.completed_at = datetime.now(UTC)
            await self.session.flush()
            return {"status": "completed", "evaluation": evaluation, "transcript": transcript}

        next_q = await self._next_question(session)
        await self.session.flush()
        return {"status": "active", "evaluation": evaluation, **next_q}

    async def _next_question(self, session: OralExamSessionModel) -> dict:
        asked_ids = [
            UUID(item["concept_id"])
            for item in (session.transcript or [])
            if item.get("concept_id")
        ]
        pair = await self.question_gen.get_random_question(session.subject_id, asked_ids)
        if not pair:
            session.status = "completed"
            session.completed_at = datetime.now(UTC)
            return {"question": None, "concept_title": None, "done": True}
        q_model, concept = pair
        session.current_concept_id = concept.id
        return {
            "question": q_model.question_text,
            "concept_id": concept.id,
            "concept_title": concept.title,
            "model_answer_hint": q_model.model_answer_hint,
            "done": False,
        }

    @staticmethod
    def _evaluate(answer: str, definition: str | None) -> dict:
        if not answer.strip():
            return {"score": 0.0, "feedback": "No se recibió respuesta.", "coverage": 0.0}
        if not definition:
            return {"score": 0.5, "feedback": "Respuesta registrada. Revise con la definición canónica.", "coverage": 0.0}

        def tokens(text: str) -> set[str]:
            return {w for w in re.findall(r"[a-záéíóúñ]{4,}", text.lower()) if len(w) >= 4}

        answer_t = tokens(answer)
        def_t = tokens(definition)
        if not def_t:
            return {"score": 0.5, "feedback": "Respuesta registrada.", "coverage": 0.0}
        overlap = len(answer_t & def_t) / len(def_t)
        score = min(1.0, overlap * 1.2 + (0.1 if len(answer.split()) > 20 else 0))
        if score >= 0.6:
            feedback = "Buena cobertura de la definición canónica. Profundice en matices."
        elif score >= 0.35:
            feedback = "Respuesta parcial. Integre más elementos de la definición oficial."
        else:
            feedback = "Respuesta insuficiente. Revise la definición en Flashcards y Apuntes."
        return {"score": round(score, 2), "feedback": feedback, "coverage": round(overlap, 2)}
