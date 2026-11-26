# Feature 003 Plan

## Backend

- Add `creator_evidence` with an ownership relationship to the creator watchlist.
- Add creator update and evidence CRUD endpoints.
- Retain content-project CRUD and expose all fields in the owner interface.
- Add double-submit CSRF protection for authenticated mutations.
- Publish provider-neutral metric definitions.

## Frontend

- Add content editor drawer with save and delete controls.
- Add creator research drawer with evidence capture and deletion.
- Keep failed forms open and present errors beside the affected form.
- Replace placeholder calendar placement with date-derived month grids.
- Add success notifications and filtered calendar views.

## Verification

- Backend contract and integration tests.
- Calendar date tests.
- Production TypeScript build and lint.
- Browser walkthrough of the complete local workflow.
