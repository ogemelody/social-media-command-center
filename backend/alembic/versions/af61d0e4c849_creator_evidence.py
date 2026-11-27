"""creator evidence

Revision ID: af61d0e4c849
Revises: 95b1f2d69c7a
Create Date: 2026-11-25 18:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "af61d0e4c849"
down_revision: str | Sequence[str] | None = "95b1f2d69c7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "creator_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("creator_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("public_metrics", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["creator_watchlist_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("creator_evidence")
