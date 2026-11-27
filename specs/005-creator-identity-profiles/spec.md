# Feature 005 — Canonical Creator Identity Profiles

## Goal

Represent each real creator once while attaching their YouTube, Instagram, TikTok and LinkedIn profiles to that canonical creator record.

## User story

As the single owner, I want one research profile per creator so that cross-platform evidence, inspiration notes and later content analysis are not fragmented across duplicate cards.

## Functional requirements

- FR-001: A creator contains a name, niche, inspiration/research notes and one to four platform profiles.
- FR-002: Each platform profile contains an allowed platform and a public profile URL.
- FR-003: A creator may have no more than one profile for each platform.
- FR-004: A platform URL may belong to only one creator.
- FR-005: Equivalent creator names cannot be added as separate records.
- FR-006: Existing duplicate creator records are merged during migration by normalized identity.
- FR-007: Evidence belonging to a merged duplicate is reassigned to the retained creator.
- FR-008: Distinct inspiration notes and all platform links are retained during migration.
- FR-009: Creator cards and the research drawer expose every attached platform.
- FR-010: Adding, editing and removing platform links is supported in the creator form.

## Guardrails

- Public platform links do not authorize scraping or access to private metrics.
- Duplicate detection is deterministic and does not use AI inference.
- Creator deletion continues to delete that creator's profiles and evidence.

## Acceptance criteria

1. Keerti Purswani appears once with both YouTube and Instagram links.
2. Darshil Parmar appears once with every saved platform link.
3. Existing evidence and inspiration notes remain available after migration.
4. Attempting to create the same normalized creator again returns a conflict.
5. Backend tests, frontend tests, lint, build and the Alembic migration pass.
