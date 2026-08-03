"""Migración: vínculos concepto ↔ chunks de Apuntes."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_concept_chunk_links"
down_revision: Union[str, None] = "002_concepts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "concept_chunk_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("concept_id", sa.UUID(), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.UUID(), sa.ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("match_type", sa.String(32), nullable=False, default="TITLE_MENTION"),
        sa.Column("relevance_score", sa.Float(), default=0.0),
        sa.Column("excerpt", sa.Text()),
        sa.Column("provenance", sa.dialects.postgresql.JSONB(), nullable=False, default={}),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concept_id", "chunk_id"),
    )
    op.create_index("idx_concept_chunk_links_concept", "concept_chunk_links", ["concept_id"])
    op.create_index("idx_concept_chunk_links_chunk", "concept_chunk_links", ["chunk_id"])


def downgrade() -> None:
    op.drop_table("concept_chunk_links")
