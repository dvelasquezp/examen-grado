"""Migración: estudio, progreso y preguntas."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_study"
down_revision: Union[str, None] = "003_concept_chunk_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_concept_progress",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("concept_id", sa.UUID(), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ease_factor", sa.Float(), default=2.5),
        sa.Column("interval_days", sa.Integer(), default=0),
        sa.Column("repetitions", sa.Integer(), default=0),
        sa.Column("mastery_score", sa.Float(), default=0.0),
        sa.Column("next_review_at", sa.DateTime(timezone=True)),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concept_id"),
    )
    op.create_index("idx_progress_next_review", "user_concept_progress", ["next_review_at"])

    op.create_table(
        "exam_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("concept_id", sa.UUID(), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("model_answer_hint", sa.Text()),
        sa.Column("question_type", sa.String(32), default="ORAL"),
        sa.Column("difficulty", sa.SmallInteger(), default=3),
        sa.Column("source_type", sa.String(32), default="TEMPLATE"),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), default={}),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_exam_questions_subject", "exam_questions", ["subject_id"])
    op.create_index("idx_exam_questions_concept", "exam_questions", ["concept_id"])

    op.create_table(
        "oral_exam_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("status", sa.String(32), default="active"),
        sa.Column("questions_asked", sa.Integer(), default=0),
        sa.Column("current_concept_id", sa.UUID(), sa.ForeignKey("concepts.id")),
        sa.Column("transcript", sa.dialects.postgresql.JSONB(), default=[]),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("oral_exam_sessions")
    op.drop_table("exam_questions")
    op.drop_table("user_concept_progress")
