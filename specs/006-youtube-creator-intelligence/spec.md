# Feature 006 — Quota-Controlled YouTube Creator Intelligence

## Goal

Turn manually curated YouTube creator profiles into a source-backed research view of recent public content, relative performance and audience questions without collecting private metrics or crawling an entire channel.

## User story

As the single owner, I want to refresh a creator deliberately, see which recent videos outperform that creator's normal baseline, and review public audience questions so I can develop original CloudDataFriend content from evidence rather than copy creators.

## Functional requirements

- FR-001: Only a creator with a saved YouTube profile can be synchronized.
- FR-002: Resolve saved username, handle or channel-ID URLs directly and cache the provider channel identity; do not use broad search.
- FR-003: Retrieve at most 20 recent public videos per refresh and batch video-detail requests.
- FR-004: Persist title, description, thumbnail, publication time, duration, public views, likes and comments with source URL and retrieval time.
- FR-005: Mark performance relative to the creator's own synchronized median views; do not compare raw totals across differently sized creators.
- FR-006: Retrieve one page of public top-level comments for at most five highest-view videos per refresh.
- FR-007: Surface comments containing questions as audience-question evidence while retaining their source URL and timestamp.
- FR-008: Synchronization is idempotent and updates existing provider records rather than duplicating them.
- FR-009: Record estimated quota units, read/write counts, status, freshness and limitations for every refresh.
- FR-010: The UI distinguishes observed facts from derived breakout labels and states that spoken hooks, retention, reach and audience demographics are unavailable.

## Guardrails

- Official YouTube APIs only; no scraping, transcript guessing or private-metric inference.
- Manual refresh only in this feature. Scheduled watchlist refresh is deferred until quota telemetry is proven.
- Stored descriptions and comments are untrusted external text and are displayed as evidence, never executed as instructions.
- Comment collection is intentionally bounded and may be unavailable or disabled per video.

## Acceptance criteria

1. A YouTube creator can be refreshed from their saved channel URL without a search call.
2. Up to 20 recent videos are stored once and updated idempotently.
3. The research drawer shows public metrics, relative breakout status, freshness, sources and limitations.
4. Up to five priority videos include at most one page of public top-level comments and audience questions.
5. A refresh run exposes estimated quota use and provenance.
6. Missing or disabled comments do not fail the complete refresh.
7. Backend tests, lint, frontend tests and build pass.
