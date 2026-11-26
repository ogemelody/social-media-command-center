# Local Development

## Prerequisites

- Python 3.12 or newer.
- Node.js 20 or newer.
- Docker Desktop for the PostgreSQL compose path.
- Google Cloud project with YouTube Data API v3 and YouTube Analytics API enabled.

## Configure secrets

1. For Docker Compose, copy `.env.example` to `.env`. For the local preview, use
   `backend/.env`. Both files are ignored by Git.
2. Generate a session secret and Fernet key using the commands documented in `.env.example`.
3. Generate the owner password hash:

   ```bash
   cd backend
   ../.venv/bin/python -m app.core.password_tool
   ```

4. Add the Google OAuth web client ID and secret.
5. Register the redirect URI for the mode you run:
   - Preview: `http://127.0.0.1:8001/api/youtube/callback`
   - Docker Compose: `http://localhost:8000/api/youtube/callback`

Never commit `.env` or paste its values into issues, chat, logs, screenshots, or test fixtures.

## Docker Compose

From the repository root:

```bash
docker compose up --build
```

Open `http://localhost:5173`.

## Local preview

To inspect the interface without Google credentials:

```bash
./scripts/start-preview.sh
```

The command prints temporary local login credentials. Keep that terminal open while using the
preview. Without `backend/.env`, YouTube uses disabled placeholders.

To activate real YouTube access from a downloaded Google Web application credentials file:

```bash
.venv/bin/python scripts/configure-google-oauth.py /path/to/client_secret.json
./scripts/start-preview.sh
```

The importer writes only to the ignored `backend/.env`, applies owner-only file permissions and
does not display credential values. When configured, the preview retains encrypted OAuth tokens
across restarts and checks once per minute whether the latest successful synchronization is more
than 24 hours old. The scheduler only runs while CommandOS is running.

The preview SQLite database is for local evaluation. Use the Docker Compose PostgreSQL service and
Alembic migrations for durable deployment.

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
