"""Progreso de estudio y estadísticas."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.knowledge_models import ConceptChunkLinkModel, ConceptModel
from src.infrastructure.persistence.postgres.study_models import UserConceptProgressModel


class ProgressService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_subject_stats(self, subject_id: UUID) -> dict:
        total = await self.session.scalar(
            select(func.count(ConceptModel.id)).where(ConceptModel.subject_id == subject_id)
        ) or 0

        with_links = await self.session.scalar(
            select(func.count(func.distinct(ConceptChunkLinkModel.concept_id)))
            .join(ConceptModel, ConceptChunkLinkModel.concept_id == ConceptModel.id)
            .where(ConceptModel.subject_id == subject_id)
        ) or 0

        progress_rows = await self.session.execute(
            select(UserConceptProgressModel)
            .join(ConceptModel, UserConceptProgressModel.concept_id == ConceptModel.id)
            .where(ConceptModel.subject_id == subject_id)
        )
        progress = list(progress_rows.scalars().all())

        now = datetime.now(UTC)
        due = sum(
            1 for p in progress if p.next_review_at is None or p.next_review_at <= now
        )
        mastered = sum(1 for p in progress if p.mastery_score >= 0.8)
        avg_mastery = (
            sum(p.mastery_score for p in progress) / len(progress) if progress else 0.0
        )

        readiness = min(1.0, (total / 150) * 0.5 + (with_links / max(total, 1)) * 0.3 + avg_mastery * 0.2)

        return {
            "concepts_total": total,
            "concepts_with_notes": with_links,
            "cards_reviewed": len(progress),
            "cards_due": due if progress else total,
            "concepts_mastered": mastered,
            "readiness_score": round(readiness, 2),
            "retention_score": round(avg_mastery, 2),
            "streak_days": 1 if progress else 0,
        }

    async def get_next_flashcard(self, subject_id: UUID) -> ConceptModel | None:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(ConceptModel)
            .outerjoin(UserConceptProgressModel, UserConceptProgressModel.concept_id == ConceptModel.id)
            .where(ConceptModel.subject_id == subject_id)
            .where(
                (UserConceptProgressModel.id.is_(None))
                | (UserConceptProgressModel.next_review_at.is_(None))
                | (UserConceptProgressModel.next_review_at <= now)
            )
            .order_by(UserConceptProgressModel.next_review_at.nulls_first(), ConceptModel.title)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def record_review(self, concept_id: UUID, quality: int) -> UserConceptProgressModel:
        """SM-2 simplificado. quality: 0-5."""
        result = await self.session.execute(
            select(UserConceptProgressModel).where(UserConceptProgressModel.concept_id == concept_id)
        )
        prog = result.scalar_one_or_none()
        if not prog:
            prog = UserConceptProgressModel(concept_id=concept_id)
            self.session.add(prog)

        q = max(0, min(5, quality))
        if q < 3:
            prog.repetitions = 0
            prog.interval_days = 1
        else:
            if prog.repetitions == 0:
                prog.interval_days = 1
            elif prog.repetitions == 1:
                prog.interval_days = 3
            else:
                prog.interval_days = max(1, int(prog.interval_days * prog.ease_factor))
            prog.repetitions += 1
            prog.ease_factor = max(1.3, prog.ease_factor + 0.1 - (5 - q) * 0.08)

        prog.mastery_score = min(1.0, prog.mastery_score + (q - 2) * 0.08)
        prog.last_reviewed_at = datetime.now(UTC)
        prog.next_review_at = datetime.now(UTC) + timedelta(days=prog.interval_days)
        prog.updated_at = datetime.now(UTC)
        await self.session.flush()
        return prog
