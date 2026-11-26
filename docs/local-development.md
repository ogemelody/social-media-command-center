# Local Development

## Prerequisites

- Python 3.12 or newer.
- Node.js 20 or newer.
- Docker Desktop for the PostgreSQL compose path.
- Google Cloud project with YouTube Data API v3 and YouTube Analytics API enabled.

## Configure secrets

1. Copy `.env.example` to `.env`. The file is ignored by Git.
2. Generate a session secret and Fernet key using the commands documented in `.env.example`.
3. Generate the owner password hash:

   ```bash
   cd backend
   ../.venv/bin/python -m app.core.password_tool
   ```

4. Add the Google OAuth web client ID and secret.
5. Register `http://localhost:8000/api/youtube/callback` as an authorized redirect URI.

Never commit `.env` or paste its values into issues, chat, logs, screenshots, or test fixtures.

## Docker Compose

From the repository root:

```bash
docker compose up --build
```

Open `http://localhost:5173`.

## UI-only preview

To inspect the interface without configuring Google credentials:

```bash
./scripts/start-preview.sh
```

The command prints temporary local login credentials. Keep that terminal open while using the preview. The YouTube connection cannot complete in preview mode because it intentionally uses dummy Google credentials.

## Run without Docker

Backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -e 'backend[dev]'
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/uvicorn app.main:app --reload
```

Frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

## Verification

```bash
.venv/bin/pytest backend/tests
.venv/bin/ruff check backend
.venv/bin/ruff format --check backend
cd frontend && npm run build && npm run lint && npm test
```

Live Google/YouTube calls are not part of ordinary automated tests. Connecting a real account requires the owner's OAuth consent.
