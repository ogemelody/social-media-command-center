# CommandOS

CommandOS is a private, single-owner Creator Intelligence and Social Media Operating System for CloudDataFriend.

Its operating loop is:

> Data collection → Research → Analysis → Recommendations → Content execution → Performance evaluation

## Current milestone

Feature 001 establishes private owner access, direct read-only YouTube connection, manual analytics synchronization, provenance, freshness, and disconnect/deletion behavior.

Feature 002 adds the full single-owner CommandOS workspace: readiness overview, honest analytics availability, creator watchlists, strategy grounding gates, a persistent content Kanban, content calendar, and configurable CloudDataFriend business context.

Feature 003 completes the pre-integration workflows with editable content briefs, deletion, creator evidence records, an accurate filtered calendar, CSRF-protected mutations and provider-neutral metric contracts.

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

No credentials belong in Git. Copy `.env.example` to an untracked `.env` for local development.
