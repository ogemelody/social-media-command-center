# CommandOS Initial Data Model

## Principles

- One owner is supported while `workspace_id` remains an isolation boundary.
- Provider-native identifiers and provenance are preserved.
- Missing data is never coerced to zero.
- External evidence is untrusted content, not instruction.
- Credentials and deletion state are separated from analytics.

## Entities

| Entity | Purpose |
|---|---|
| `users`, `workspaces` | Private owner identity and CloudDataFriend boundary |
| `provider_connections` | Provider account, encrypted credentials, scopes, expiry, status |
| `social_accounts` | Channel/profile/page identity |
| `content_items` | Provider content identity and metadata |
| `metric_definitions` | Provider key, optional canonical key, unit, scope, aggregation |
| `metric_observations` | Subject, period, value, availability, retrieval, sync lineage |
| `sync_runs`, `provider_checkpoints` | Idempotent ingestion audit and incremental state |
| `retention_rules` | Provider refresh, retention, and deletion rules |
| `creators`, `creator_accounts` | Watchlisted creators and platform identities |
| `evidence_sources`, `research_observations` | Source, timestamp, checksum, observation, limitation |
| `business_context_versions` | Versioned audience, pillars, goals, offers, and resources |
| `ai_runs`, `ai_tool_executions` | Model and validated tool audit |
| `ai_recommendations`, `recommendation_evidence` | Structured output and claim-to-evidence links |
| `content_projects`, `content_revisions` | Idea, brief, script, workflow, and calendar |
| `audit_events` | Security and consequential-action audit |

## Metric availability

- `available`: valid value, including zero.
- `unavailable`: provider does not supply it for the scope.
- `not_requested`: outside this extraction.
- `delayed`: value is not final or populated yet.
- `restricted`: plan, permission, account type, or policy prevents access.
- `error`: retrieval failed; no value is asserted.

Only `available` observations carry a numeric value. Other states keep the value null with a reason where known.

## Source precedence

Owner YouTube analytics use direct YouTube Analytics first and direct YouTube Data metadata/statistics second. Metricool remains isolated unless a later decision approves a mapped capability. Provider-native observations remain distinct even when canonical mappings exist.

## Deletion

Disconnect immediately disables jobs, attempts token revocation, removes credentials, and starts provider-specific data deletion. Minimal non-sensitive audit evidence may remain where permitted.

## Implemented local workflow records

- `creator_watchlist_items` stores a provider-neutral creator identity, niche and owner-authored inspiration notes.
- `creator_platform_profiles` stores one public profile URL per platform for a creator. A creator is represented once even when researched across several platforms.
- `creator_evidence` stores a public source URL, factual observation, observation time, available public metrics, and explicit limitations. Creator deletion cascades to profiles and evidence records.
- `creator_research_runs` records the status, estimated quota units, freshness and row counts for each deliberate provider refresh.
- `creator_videos` stores bounded public YouTube video snapshots with source provenance; `creator_video_comments` stores the bounded top-level comment sample used to identify audience questions. Both are deleted with their canonical creator.
- `content_projects` stores the platform, type, pillar, hook, brief, evidence URL, planned date, publishing URL, and production status. Calendar placement is derived directly from `planned_for`.
