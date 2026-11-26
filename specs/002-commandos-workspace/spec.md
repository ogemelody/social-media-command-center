# Feature 002 — CommandOS Product Workspace

## Objective

Turn the YouTube integration foundation into a useful single-owner operating workspace spanning analytics, creator research, grounded strategy readiness, content production and business context.

## User stories

1. As the owner, I can see which parts of my intelligence loop are ready and what needs attention.
2. As the owner, I can inspect owned analytics without missing metrics being displayed as zero.
3. As the owner, I can maintain a creator watchlist with public source URLs and research notes.
4. As the owner, I can capture content ideas and move them through an explicit production workflow.
5. As the owner, I can see planned content on a calendar while publishing remains manual.
6. As the owner, I can configure CloudDataFriend audience, pillars, goals, offers and resources.
7. As the owner, I can see whether enough evidence exists for AI strategy generation.

## Functional requirements

- FR-001: Provide product navigation for Overview, My Analytics, Creator Intelligence, AI Strategist, Content Studio, Calendar and Business Context.
- FR-002: Persist creator watchlist records with platform, source URL, niche, notes and timestamps.
- FR-003: Persist content projects with platform, workflow status, pillar, planning date and optional evidence/publishing URLs.
- FR-004: Persist one owner-scoped business context record.
- FR-005: Derive workspace readiness from stored state; do not hard-code completed states.
- FR-006: Display unavailable analytics as unavailable, never as numeric zero.
- FR-007: Keep AI strategy generation disabled until owned analytics, business context and creator research exist.
- FR-008: Keep all external platform access read-only and clearly label integrations that are planned or awaiting feasibility validation.
- FR-009: Preserve the existing YouTube connection, synchronization, provenance and disconnect workflows.
- FR-010: Support desktop and mobile layouts.

## Non-goals

- AI recommendation generation itself.
- Automated social publishing.
- Instagram, TikTok or LinkedIn ingestion.
- Automated creator scraping or private creator analytics.
- Metricool production ingestion before the approved feasibility spike.

## Acceptance criteria

- The owner can create a creator record and retrieve it after refresh.
- The owner can create a content item and move it between all workflow states.
- The owner can save business context and see overview readiness update.
- Analytics cards show an em dash and "Data unavailable" when no observation exists.
- The strategist separates observations, interpretations and actions and does not generate unsupported output.
- Backend, frontend, migration and lint/test checks pass.
