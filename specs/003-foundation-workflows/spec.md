# Feature 003 — Foundation Workflow Completion

## Objective

Complete CommandOS local workflows before external platform credentials and live analytics are introduced.

## User stories

1. As the owner, I can edit and permanently delete a content item.
2. As the owner, I can develop a content item with a hook, brief, pillar, type, evidence URL, publishing URL and planned date.
3. As the owner, I can edit a creator and maintain multiple timestamped evidence records.
4. As the owner, I can distinguish factual observations, public metrics and limitations for every creator source.
5. As the owner, I can view content on its actual calendar date and filter the calendar.
6. As the owner, I receive clear success or error feedback for changes.

## Functional requirements

- FR-001: Content Studio exposes create, read, update and delete workflows.
- FR-002: A failed save keeps its form open and displays the error.
- FR-003: Creator profiles expose edit and delete workflows.
- FR-004: Creator evidence requires a source URL, observation timestamp, factual observation and limitations.
- FR-005: Creator deletion cascades to its evidence records.
- FR-006: Calendar cells are generated Monday-first and content is keyed by its actual local date.
- FR-007: Calendar supports month navigation and platform/status filters.
- FR-008: All authenticated mutations require a matching CSRF cookie and header.
- FR-009: Metric definitions are explicit and provider-neutral.

## Non-goals

- Live YouTube, Instagram, TikTok or LinkedIn credentials.
- Automated research or scraping.
- AI strategy generation.
- Automated social publishing.

## Acceptance criteria

- An owner can create, edit, schedule, move and delete content through the UI.
- An owner can add creator evidence with a public source and limitations.
- Content dated 2026-12-03 appears on the December 3 calendar cell.
- A mutation without a CSRF token is rejected.
- Database migrations, backend tests, frontend tests, lint and production build pass.
