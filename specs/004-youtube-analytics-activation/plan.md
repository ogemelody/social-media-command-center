# Feature 004 Plan

## Backend

- Add a date-range analytics read model for period totals, daily views and ranked content.
- Normalize datetime serialization to explicit UTC.
- Reject invalid custom ranges and cap analytics windows.
- Prevent concurrent manual or scheduled synchronization runs.
- Classify provider errors into safe owner-facing categories.
- Add a lightweight in-process daily scheduler backed by persisted sync history.

## Frontend

- Replace the placeholder with a responsive views trend chart.
- Add preset and custom date controls.
- Add unit-aware KPI formatting and a top-content table.
- Refresh analytics, overview and history when synchronization reaches a terminal state.
- Disable the sync action while queued or running and display safe errors in the audit trail.

## Operations

- Keep real secrets in the ignored `backend/.env` for preview.
- Keep PostgreSQL and Alembic as the durable deployment path.
- Document Google OAuth activation, local preview and scheduled-sync behavior.

## Verification

- Analytics aggregation and custom-range API tests.
- Sync concurrency and scheduler tests.
- Unit-formatting and range-control frontend tests.
- Live read-only YouTube smoke test against the connected CloudDataFriend channel.
- Full backend and frontend quality gates.

