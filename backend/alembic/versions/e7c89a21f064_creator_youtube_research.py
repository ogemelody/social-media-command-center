"""creator youtube research

Revision ID: e7c89a21f064
Revises: d6b2409e7f51
Create Date: 2026-11-26 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e7c89a21f064"
down_revision: str | Sequence[str] | None = "d6b2409e7f51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("creator_platform_profiles", sa.Column("provider_account_id", sa.String(255)))
    op.add_column("creator_platform_profiles", sa.Column("uploads_playlist_id", sa.String(255)))
    op.add_column(
        "creator_platform_profiles", sa.Column("last_synced_at", sa.DateTime(timezone=True))
    )
    op.create_table(
        "creator_research_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "creator_id",
            sa.String(36),
            sa.ForeignKey("creator_watchlist_items.id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("estimated_quota_units", sa.Integer(), nullable=False),
        sa.Column("records_read", sa.Integer(), nullable=False),
        sa.Column("records_written", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "creator_videos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "creator_id",
            sa.String(36),
            sa.ForeignKey("creator_watchlist_items.id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_video_id", sa.String(255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("views", sa.Integer()),
        sa.Column("likes", sa.Integer()),
        sa.Column("comments_count", sa.Integer()),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "provider_video_id"),
    )
    op.create_table(
        "creator_video_comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("video_id", sa.String(36), sa.ForeignKey("creator_videos.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_comment_id", sa.String(255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(255)),
        sa.Column("like_count", sa.Integer()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "provider_comment_id"),
    )


def downgrade() -> None:
    op.drop_table("creator_video_comments")
    op.drop_table("creator_videos")
    op.drop_table("creator_research_runs")
    op.drop_column("creator_platform_profiles", "last_synced_at")
    op.drop_column("creator_platform_profiles", "uploads_playlist_id")
    op.drop_column("creator_platform_profiles", "provider_account_id")
