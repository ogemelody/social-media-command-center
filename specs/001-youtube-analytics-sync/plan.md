# Feature 001 Implementation Plan

**Status:** Accepted for incremental implementation

## Decisions

- Modular monolith with React, FastAPI, PostgreSQL, and a separate worker boundary.
- Private owner authentication is a password-derived server session for the local MVP; production may replace it behind the same identity interface.
- Direct YouTube APIs are authoritative; Metricool is excluded.
- Provider tokens use authenticated encryption with an environment-managed key.
- Manual sync executes through a service abstraction; deployment will move execution to a separate worker process.

## Flow

1. Owner authenticates with CommandOS.
2. Backend starts Google OAuth with short-lived state and PKCE verifier.
3. Callback exchanges the code, encrypts tokens, and discovers the channel.
4. Owner creates a sync run.
5. Sync service retrieves channel/video metadata and daily analytics.
6. Bounded transactional upserts preserve provenance and idempotency.
7. UI displays connection, run state, freshness, and disconnect.

## Initial metric contract

- Channel ID and title.
- Video ID, title, publish time, duration, and URL.
- Daily views, estimated minutes watched, average view duration, likes, comments, subscribers gained, and subscribers lost when supported.

Audience demographics, retention curves, revenue, and transcript handling are deferred.

## Security

- Password hash comparison, signed HttpOnly session cookie, secure-cookie configuration for production.
- OAuth state and PKCE, backend exchanges, token encryption, and redaction.
- Read-only scopes only.
- Owner authorization repeated for all connection/sync/deletion actions.

## Testing

- Unit: crypto, authentication, state, transformations, availability, idempotency.
- Contract: sanitized YouTube response fixtures.
- Integration: database uniqueness, sync states, disconnect and deletion.
- Frontend: owner journey and error states when dependencies are installed.
- Live provider: opt-in only and never ordinary CI.

## Known rollout boundary

Feature 001 runs with SQLite in zero-dependency local/test mode and supports PostgreSQL through configuration once SQLAlchemy/Alembic dependencies are installed. Production deployment and scheduled execution remain separately authorized.
