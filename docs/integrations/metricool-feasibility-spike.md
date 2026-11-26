# Metricool Controlled Feasibility Spike

**Status:** Approved to plan; not executed

**Endpoint:** `https://ai.metricool.com/mcp`
**Mode:** Read-only inspection

## Objective

Determine whether Metricool can safely provide optional secondary analytics or future cross-platform capabilities without making CommandOS dependent on it.

The spike does not authorize publishing, scheduling, editing, messaging, account mutation, permanent production ingestion, or a paid purchase.

## Preconditions

- Owner reviews the OAuth permission screen on the official Metricool domain.
- Credentials never enter chat, terminal history, tracked files, or logs.
- Expected read-only tools and stop conditions are reviewed first.

## Validation matrix

| Area | Evidence required |
|---|---|
| Authentication | OAuth flow, permissions, revocation, refresh behavior |
| Brands | Returned brands, connected networks, plan limitations |
| Tools | Every tool name/schema classified as read, write, destructive, or ambiguous |
| Analytics | Metrics, definitions, dates, aggregation, pagination, freshness, limits |
| Competitors | Official hosted MCP coverage, fields, history, URLs, timestamps |
| Storage | Written permission, retention, refresh, and deletion obligations |
| Automation | Custom-backend use, unattended refresh, request/tool-call limits |
| Reconciliation | Small date-range comparison with direct YouTube definitions |

Only allowlisted read-only tools may be called. Planner, publishing, update, delete, messaging, and ad-management tools are prohibited.

## Pass criteria

1. Authentication and revocation are reliable.
2. CommandOS can enforce a read-only allowlist.
3. Metrics and schemas can be validated and mapped explicitly.
4. Provenance, freshness, and limitations can be preserved.
5. Scheduled execution is supported or a manual-only role is accepted.
6. Storage and retention permissions are documented.
7. No purchase is assumed.

## Stop conditions

Stop for a non-official domain, credential exposure, required write action, ambiguous mutation, incompatible terms, or unapproved purchase.

## Outcomes

- `APPROVE_MANUAL_SECONDARY`
- `APPROVE_SCHEDULED_SECONDARY`
- `APPROVE_NON_YOUTUBE_ONLY`
- `REJECT_PRODUCTION_USE`
- `INSUFFICIENT_EVIDENCE`
