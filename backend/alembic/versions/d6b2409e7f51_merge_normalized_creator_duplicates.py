"""merge normalized creator duplicates

Revision ID: d6b2409e7f51
Revises: c4a7e9d281f3
Create Date: 2026-11-26 14:18:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d6b2409e7f51"
down_revision: str | Sequence[str] | None = "c4a7e9d281f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def normalized_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def display_name_score(value: str) -> tuple[int, int, int]:
    return (
        int(any(character.isspace() for character in value)),
        int(not any(character in "._-" for character in value)),
        sum(character.isupper() for character in value),
    )


def upgrade() -> None:
    connection = op.get_bind()
    creators = connection.execute(
        sa.text(
            """
            SELECT id, name, notes, evidence_checked_at, created_at
            FROM creator_watchlist_items
            ORDER BY created_at, id
            """
        )
    ).mappings().all()

    canonical_by_name: dict[str, str] = {}
    canonical_display_names: dict[str, str] = {}
    notes_by_creator: dict[str, list[str]] = {}

    for creator in creators:
        identity = normalized_name(creator["name"])
        canonical_id = canonical_by_name.setdefault(identity, creator["id"])
        canonical_name = canonical_display_names.setdefault(identity, creator["name"])
        notes = notes_by_creator.setdefault(canonical_id, [])
        note = (creator["notes"] or "").strip()
        if note and note not in notes:
            notes.append(note)

        if creator["id"] == canonical_id:
            continue

        if display_name_score(creator["name"]) > display_name_score(canonical_name):
            connection.execute(
                sa.text("UPDATE creator_watchlist_items SET name = :name WHERE id = :id"),
                {"id": canonical_id, "name": creator["name"]},
            )
            canonical_display_names[identity] = creator["name"]

        duplicate_profiles = connection.execute(
            sa.text(
                """
                SELECT id, platform
                FROM creator_platform_profiles
                WHERE creator_id = :duplicate_id
                """
            ),
            {"duplicate_id": creator["id"]},
        ).mappings().all()
        canonical_platforms = {
            row["platform"]
            for row in connection.execute(
                sa.text(
                    """
                    SELECT platform
                    FROM creator_platform_profiles
                    WHERE creator_id = :canonical_id
                    """
                ),
                {"canonical_id": canonical_id},
            ).mappings()
        }
        for profile in duplicate_profiles:
            if profile["platform"] in canonical_platforms:
                connection.execute(
                    sa.text("DELETE FROM creator_platform_profiles WHERE id = :profile_id"),
                    {"profile_id": profile["id"]},
                )
            else:
                connection.execute(
                    sa.text(
                        """
                        UPDATE creator_platform_profiles
                        SET creator_id = :canonical_id
                        WHERE id = :profile_id
                        """
                    ),
                    {"canonical_id": canonical_id, "profile_id": profile["id"]},
                )
                canonical_platforms.add(profile["platform"])

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


def downgrade() -> None:
    # Identity merges are intentionally irreversible: recreating duplicates would
    # invent ownership for evidence and profiles that were consolidated.
    pass
