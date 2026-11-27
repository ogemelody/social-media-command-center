# CommandOS

CommandOS is a private, single-owner Creator Intelligence and Social Media Operating System for CloudDataFriend.

Its operating loop is:

> Data collection → Research → Analysis → Recommendations → Content execution → Performance evaluation

## Current milestone

Feature 001 establishes private owner access, direct read-only YouTube connection, manual analytics synchronization, provenance, freshness, and disconnect/deletion behavior.

Feature 002 adds the full single-owner CommandOS workspace: readiness overview, honest analytics availability, creator watchlists, strategy grounding gates, a persistent content Kanban, content calendar, and configurable CloudDataFriend business context.

Feature 003 completes the pre-integration workflows with editable content briefs, deletion, creator evidence records, an accurate filtered calendar, CSRF-protected mutations and provider-neutral metric contracts.

Feature 004 activates the direct YouTube analytics experience with selectable reporting periods,
daily performance trends, top-content ranking, explicit metric units, overlap-safe manual sync and a
lightweight daily scheduler. PostgreSQL remains the durable deployment database; the preview uses
SQLite for local evaluation.

Feature 005 establishes canonical creator identities so one creator can hold multiple public platform
profiles without fragmenting evidence, inspiration notes or future cross-platform analysis.

Feature 006 adds deliberate, quota-controlled YouTube creator research: recent public videos, relative
breakout signals, bounded public-comment samples, audience questions, freshness and source provenance.

Direct YouTube APIs are authoritative. Metricool is an optional secondary provider pending a controlled feasibility spike; it is not an automatic failover.

## Repository map

- `backend/` — FastAPI modular monolith and worker services.
- `frontend/` — React and TypeScript owner interface.
- `docs/product/PRD.md` — approved product direction.
- `docs/architecture.md` — MVP architecture.
- `docs/data-model.md` — initial domain model.
- `docs/adr/` — architecture decisions.
- `docs/integrations/metricool-feasibility-spike.md` — read-only spike protocol.
- `specs/001-youtube-analytics-sync/` — Feature 001 specification, plan, and tasks.
- `specs/002-commandos-workspace/` — Feature 002 specification, plan, and tasks.
- `specs/003-foundation-workflows/` — Feature 003 specification, plan, and tasks.
- `specs/004-youtube-analytics-activation/` — Feature 004 specification, plan, and tasks.
- `specs/005-creator-identity-profiles/` — Feature 005 specification, plan, and tasks.
- `specs/006-youtube-creator-intelligence/` — Feature 006 specification, plan, and tasks.

No credentials belong in Git. Copy `.env.example` to an untracked `.env` for local development.

The local preview stores durable application state in the ignored `.data/commandos-preview.db`
file. Stopping or restarting the preview does not delete connections, creator profiles or analytics.
Deleting that file intentionally resets the local workspace.
