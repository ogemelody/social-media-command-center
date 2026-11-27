# CommandOS Product Requirements Document

**Version:** 0.2

**Status:** Approved for Feature 001

**Date:** 25 November 2026
**Deployment:** Private, single owner

## Product vision

CommandOS is CloudDataFriend's private, AI-powered Creator Intelligence and Social Media Operating System. It turns analytics and permitted creator research into evidence-backed content decisions and a managed production workflow.

The operating loop is:

> Data collection → Research → Analysis → Recommendations → Content execution → Performance evaluation

## Principles

1. Official direct APIs are preferred.
2. Direct YouTube APIs are authoritative for YouTube.
3. Metricool remains optional until a controlled spike validates it.
4. An unavailable metric is never represented as zero.
5. Observations, AI interpretations, and recommendations remain distinct.
6. Research includes source, timestamp, evidence, freshness, and limitations.
7. No unauthorized scraping or unofficial platform APIs.
8. Publishing and audience communication remain manual in the MVP.

## Owner and context

The MVP serves one authenticated CloudDataFriend owner and one private workspace. The internal model retains `workspace_id` as an isolation boundary but does not implement teams, invitations, billing, or SaaS tenancy.

Configurable business context includes target audiences, content pillars, goals, services, products, educational resources, preferred formats, tone, constraints, and calls to action.

## Platform sequence

1. YouTube — first direct integration and authoritative analytics source.
2. Instagram — later direct integration or validated Metricool adapter.
3. TikTok — later authorized integration with manual-research fallback.
4. LinkedIn — secondary, subject to approved API access.

Research niches are Data Engineering, AI Engineering and AI Agents, Cloud Computing and DevOps, Technology Careers, Building in Public, and Women in Tech.

## MVP modules

### Private owner access

- Backend-enforced access for the configured owner.
- Secure, revocable sessions.
- Provider authorization remains separate from CommandOS login.

### My Analytics

- Official account and content performance data.
- Manual and scheduled synchronization.
- Trends, growth where available, top content, posting patterns, date filters, metric definitions, freshness, and sync history.
- Explicit missing, delayed, restricted, and unavailable states.

### Creator Intelligence

- Creator discovery and manually curated watchlists.
- Profiles, public content, topics, formats, posting behaviour, public metrics, breakout analysis, emerging trends, audience questions where accessible, gaps, and opportunities.
- Every result includes evidence and data limitations.
- Private metrics, reach, retention, transcripts, and demographics are never invented.

### AI Content Strategist

- Weekly summaries, niche reports, opportunities, hooks, titles, platform strategies, briefs, and experiments.
- Structured outputs, explicit tool contracts, evidence references, tool logs, freshness, prompt-injection controls, and cost limits.
- Quantitative calculations remain deterministic application logic.

### Content Studio

- Ideas, approved recommendations, briefs, scripts, Kanban production status, and content calendar.
- Publishing remains manual.

### Business context

- Versioned CloudDataFriend audience, pillars, goals, offers, resources, and constraints.
- External content cannot update business context automatically.

## Data engineering requirements

- Capability-aware provider adapters.
- Validated schemas and idempotent incremental synchronization.
- Deduplication, bounded retries, rate-limit handling, checkpoints, and sync logs.
- Source provenance, metric definitions, and provider-specific retention rules.
- `available`, `unavailable`, `not_requested`, `delayed`, `restricted`, and `error` metric states.
- Raw payload retention only when permitted and justified.

## YouTube and Metricool policy

The YouTube Data API and YouTube Analytics API are authoritative for the owner's YouTube account.

Metricool is not an automatic failover. If its spike succeeds, it may become a manually selected secondary source, a reconciliation source, or a source for explicitly labelled Metricool-only capabilities. CommandOS must never silently merge or replace direct YouTube observations with Metricool observations. A source switch records provider, reason, range, mapping, and provenance.

## Security and AI quality

- Read-only provider scopes.
- Backend-only OAuth and token refresh.
- Encrypted token storage and redacted logs.
- Revocation, disconnect, and deletion workflows.
- JSON-schema outputs and validated tools.
- Evidence identifiers on factual claims.
- No arbitrary SQL, shell execution, or instructions from retrieved content.
- AI evaluation fixtures for insufficient, conflicting, unavailable, and malicious evidence.

## MVP exclusions

- Manychat-style automation, automatic follow-back, and follower messaging.
- Automated publishing.
- Multi-user SaaS, billing, AI CFO/COO, and advanced multi-agent orchestration.
- Video editing and thumbnail generation.
- Unauthorized scraping or unofficial APIs.

## Approved sequence

1. Documentation and architecture.
2. Controlled Metricool feasibility spike.
3. Feature 001: private YouTube connection and analytics synchronization.
4. Analytics dashboard.
5. Business Context.
6. Creator watchlists and manual evidence.
7. YouTube Creator Intelligence.
8. AI Content Strategist.
9. Content Studio.
10. Instagram, TikTok, and LinkedIn as separately approved features.

## Deferred decisions

- Production host and authentication provider.
- Historical import window and final YouTube metric contract.
- Scheduled sync frequency.
- Metricool's approved role after the spike.
- Instagram, TikTok, and LinkedIn access outcomes.
- Production OpenAI model and budget.

## Approval record

The owner approved private single-owner scope, YouTube-first direct integration, Metricool as optional after a controlled spike, Feature 001, and revised SDD documentation. Implementation proceeds incrementally and does not authorize deployment, purchases, commits, pushes, or merges.
