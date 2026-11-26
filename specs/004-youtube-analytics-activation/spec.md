# Feature 004 — YouTube Analytics Activation

## Objective

Turn the verified read-only YouTube connection into a trustworthy analytics experience that the
owner can use to evaluate performance before AI recommendations are introduced.

## User stories

1. As the owner, I can evaluate YouTube performance over 7, 28, 90 or custom date ranges.
2. As the owner, I can see daily views and top-performing videos from my synchronized data.
3. As the owner, I can distinguish counts, minutes, seconds, percentages, zero and unavailable data.
4. As the owner, I can synchronize safely without creating overlapping ingestion runs.
5. As the owner, I can understand a failed synchronization and see its source and freshness.
6. As the owner, I can rely on a lightweight daily synchronization while CommandOS is running.

## Functional requirements

- FR-001: The analytics API accepts 7, 28, 90 and validated custom date ranges.
- FR-002: Period totals aggregate available observations without treating missing data as zero.
- FR-003: Average view duration is derived from total watch minutes and views for the selected range.
- FR-004: The response includes a daily views series and top videos ranked by views.
- FR-005: Every metric and content row includes units, availability, source and freshness context.
- FR-006: All API timestamps are serialized as explicit UTC values and displayed in the owner's local timezone.
- FR-007: Only one queued or running YouTube synchronization can exist at a time.
- FR-008: The owner interface disables synchronization while a run is active and refreshes analytics when it completes.
- FR-009: Sync failures expose safe, actionable error categories without leaking provider responses or tokens.
- FR-010: A lightweight scheduler creates a synchronization when the latest successful run is older than 24 hours.
- FR-011: Scheduled and manual runs use the same idempotent provider ingestion service.
- FR-012: PostgreSQL remains the durable deployment database; SQLite remains a local preview option only.

## Non-goals

- OpenAI integration or generated recommendations.
- Metricool ingestion.
- Instagram, TikTok or LinkedIn analytics.
- Automated publishing or YouTube write permissions.
- Revenue metrics that require monetary scopes or YouTube Partner Program eligibility.

## Acceptance criteria

- The dashboard renders real daily views for a selected period.
- The dashboard renders top videos with links, publication dates and available metrics.
- Watch time is labelled in minutes and average view duration in seconds/minutes.
- A legitimate zero remains zero; an unavailable metric renders as unavailable.
- A second sync request during an active run returns the existing run and does not start another worker.
- A completed run automatically refreshes the dashboard and history.
- Failed runs show a safe error reason in synchronization history.
- Scheduler tests demonstrate that a due connection is synchronized and a fresh connection is skipped.
- Backend tests, frontend tests, lint, formatting and production build pass.

