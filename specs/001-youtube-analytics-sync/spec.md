# Feature 001: Private YouTube Connection and Analytics Sync

**Status:** Approved
**Authoritative provider:** Direct YouTube APIs

## Problem

The CommandOS owner needs a secure, trustworthy connection to the CloudDataFriend YouTube channel before dashboards, creator comparisons, or AI recommendations can be built.

## User stories

- As the owner, I can sign in privately.
- As the owner, I can connect YouTube with read-only permissions.
- As the owner, I can trigger and inspect a manual sync.
- As the owner, I can distinguish zero, missing, restricted, delayed, and failed metrics.
- As the owner, I can disconnect and start data deletion.

## Requirements

### Owner access

- Only the configured owner accesses protected routes.
- Authentication uses a secure server-controlled session.
- Provider authorization remains separate.

### YouTube authorization

- Official authorization-code flow with state validation and PKCE where supported.
- Least-privilege approved scopes.
- Replayed, expired, mismatched, or malformed callbacks are rejected.
- Tokens are encrypted at rest and never returned to the frontend or logs.

### Connection and synchronization

- Persist the authorized channel identity and connection health.
- Start a manual sync only when no conflicting sync is active.
- Retrieve approved channel/video metadata and analytics.
- Validate responses, persist provenance, and record run results.
- Repeated extraction creates no duplicate facts.
- Checkpoints advance only after commit.
- Partial failure preserves prior valid data.

### Metrics and failures

- Valid zero is `available` with value zero.
- Unavailable, restricted, delayed, not-requested, and failed metrics have null value.
- Retries use bounded exponential backoff with jitter.
- Authorization failures do not retry indefinitely.
- Status displays latest success, freshness, counts, and redacted errors.

### Disconnect

- Disconnect blocks new syncs immediately.
- Token revocation is attempted and audited.
- Credentials are removed and a trackable deletion workflow starts.

## Acceptance criteria

1. Non-owner protected requests are denied.
2. Successful authorization displays the channel without exposing tokens.
3. Invalid state or callback replay stores no credential.
4. Manual sync creates an asynchronous run.
5. Persisted metadata and observations match validated fixtures.
6. Repeated synchronization creates no duplicate observations.
7. Zero and unavailable values remain distinct.
8. Transient retries are bounded and recorded.
9. Revocation produces `authorization_required` without infinite retry.
10. Partial failure leaves valid data intact.
11. Status exposes freshness and redacted outcomes.
12. Disconnect blocks sync, revokes, removes credentials, and starts deletion.
13. Logs and responses contain no secrets.
14. Unit, contract, integration, security, and critical end-to-end tests pass.

## Out of scope

- Metricool ingestion or failover.
- Instagram, TikTok, LinkedIn, Creator Intelligence, AI recommendations, and a full chart dashboard.
- Recurring scheduled sync and revenue analytics.
- Publishing or any platform write operation.
- Multi-user workspaces.
