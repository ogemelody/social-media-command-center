# Feature 002 Plan

## Architecture

Extend the modular monolith rather than introducing new services. The FastAPI application owns persistence and validation; React and TanStack Query own server-state presentation and mutations.

## Data model additions

- `business_context`: one single-owner context record.
- `creator_watchlist_items`: manually curated, source-backed creator profiles.
- `content_projects`: content workflow and calendar records.

## API additions

- `GET /api/workspace/overview`
- `GET /api/analytics/summary`
- `GET|PUT /api/business-context`
- `GET|POST|DELETE /api/creators`
- `GET|POST|PATCH|DELETE /api/content-projects`

## Design system

Use the exact public website tokens observed on 2026-11-25:

- Paper: `oklch(95.83% .007 88.64)`
- Surface: `oklch(97.96% .0057 84.57)`
- Ink: `oklch(22.72% .0081 84.59)`
- Teal: `oklch(38.59% .0519 182.12)`
- Copper: `oklch(56.56% .1123 54.52)`
- Border: `oklch(86.72% .0185 89.37)`

## Safety and trust

- No seed metrics or invented creator results.
- Public creator URLs remain explicit evidence sources.
- Strategy generation is visibly gated.
- YouTube disconnect retains its confirmation and deletion behavior.
