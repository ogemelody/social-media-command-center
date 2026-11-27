"""canonical creators with multiple platform profiles

Revision ID: c4a7e9d281f3
Revises: af61d0e4c849
Create Date: 2026-11-26 14:10:00
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "c4a7e9d281f3"
down_revision: str | Sequence[str] | None = "af61d0e4c849"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def display_name_score(value: str) -> tuple[int, int, int]:
    return (
        int(any(character.isspace() for character in value)),
        int(not any(character in "._-" for character in value)),
        sum(character.isupper() for character in value),
    )


def upgrade() -> None:
    op.create_table(
        "creator_platform_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("creator_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("profile_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["creator_watchlist_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("creator_id", "platform", name="uq_creator_profile_platform"),
        sa.UniqueConstraint("platform", "profile_url", name="uq_creator_profile_url"),
    )

    connection = op.get_bind()
    creators = connection.execute(
        sa.text(
            """
            SELECT id, name, platform, profile_url, notes, evidence_checked_at, created_at
            FROM creator_watchlist_items
            ORDER BY created_at, id
            """
        )
    ).mappings().all()

    canonical_by_name: dict[str, str] = {}
    canonical_display_names: dict[str, str] = {}
    platforms_by_creator: dict[str, set[str]] = {}
    notes_by_creator: dict[str, list[str]] = {}

    for creator in creators:
        normalized_name = "".join(
            character
            for character in creator["name"].casefold()
            if character.isalnum()
        )
        canonical_id = canonical_by_name.setdefault(normalized_name, creator["id"])
        canonical_name = canonical_display_names.setdefault(normalized_name, creator["name"])
        platforms = platforms_by_creator.setdefault(canonical_id, set())
        notes = notes_by_creator.setdefault(canonical_id, [])

        note = (creator["notes"] or "").strip()
        if note and note not in notes:
            notes.append(note)

        if creator["platform"] not in platforms:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO creator_platform_profiles
                        (id, creator_id, platform, profile_url, created_at)
                    VALUES
                        (:id, :creator_id, :platform, :profile_url, :created_at)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "creator_id": canonical_id,
                    "platform": creator["platform"],
                    "profile_url": creator["profile_url"],
                    "created_at": creator["created_at"],
                },
            )
            platforms.add(creator["platform"])

        if creator["id"] != canonical_id:
            if display_name_score(creator["name"]) > display_name_score(canonical_name):
                connection.execute(
                    sa.text("UPDATE creator_watchlist_items SET name = :name WHERE id = :id"),
                    {"id": canonical_id, "name": creator["name"]},
                )
                canonical_display_names[normalized_name] = creator["name"]
            connection.execute(
                sa.text(
                    "UPDATE creator_evidence SET creator_id = :canonical_id "
                    "WHERE creator_id = :duplicate_id"
                ),
                {"canonical_id": canonical_id, "duplicate_id": creator["id"]},
            )
            connection.execute(
                sa.text(
                    """
                    UPDATE creator_watchlist_items
                    SET evidence_checked_at = COALESCE(
                        evidence_checked_at, :duplicate_checked_at
                    )
                    WHERE id = :canonical_id
                    """
                ),
                {
                    "canonical_id": canonical_id,
                    "duplicate_checked_at": creator["evidence_checked_at"],
                },
            )
            connection.execute(
                sa.text("DELETE FROM creator_watchlist_items WHERE id = :duplicate_id"),
                {"duplicate_id": creator["id"]},
            )

    for creator_id, notes in notes_by_creator.items():
        connection.execute(
            sa.text("UPDATE creator_watchlist_items SET notes = :notes WHERE id = :id"),
            {"id": creator_id, "notes": "\n\n".join(notes)},
        )

    with op.batch_alter_table("creator_watchlist_items", recreate="always") as batch_op:
        batch_op.drop_column("platform")
        batch_op.drop_column("profile_url")


def downgrade() -> None:
    with op.batch_alter_table("creator_watchlist_items", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("platform", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("profile_url", sa.Text(), nullable=True))

    connection = op.get_bind()
    creators = connection.execute(
        sa.text("SELECT id FROM creator_watchlist_items")
    ).mappings().all()
    for creator in creators:
        profile = connection.execute(
            sa.text(
                """
                SELECT platform, profile_url
                FROM creator_platform_profiles
                WHERE creator_id = :creator_id
                ORDER BY created_at, id
                LIMIT 1
                """
            ),
            {"creator_id": creator["id"]},
        ).mappings().first()
        if profile:
            connection.execute(
                sa.text(
                    """
                    UPDATE creator_watchlist_items
                    SET platform = :platform, profile_url = :profile_url
                    WHERE id = :creator_id
                    """
                ),
                {
                    "creator_id": creator["id"],
                    "platform": profile["platform"],
                    "profile_url": profile["profile_url"],
                },
            )

    with op.batch_alter_table("creator_watchlist_items", recreate="always") as batch_op:
        batch_op.alter_column("platform", nullable=False)
        batch_op.alter_column("profile_url", nullable=False)
        batch_op.create_unique_constraint(
            "uq_creator_watchlist_platform_url", ["platform", "profile_url"]
        )

    op.drop_table("creator_platform_profiles")
