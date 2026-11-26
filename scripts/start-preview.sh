#!/usr/bin/env bash
set -euo pipefail

preview_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
preview_python="$preview_root/.venv/bin/python"
preview_uvicorn="$preview_root/.venv/bin/uvicorn"
preview_password="commandos-preview-2026"
preview_frontend_port="5178"
preview_backend_port="8001"
preview_frontend_url="http://127.0.0.1:$preview_frontend_port"
preview_backend_url="http://127.0.0.1:$preview_backend_port"

if [[ ! -x "$preview_python" || ! -x "$preview_uvicorn" ]]; then
  echo "Backend dependencies are missing. Run:"
  echo "  cd $preview_root"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install -e 'backend[dev]'"
  exit 1
fi

if [[ ! -d "$preview_root/frontend/node_modules" ]]; then
  echo "Frontend dependencies are missing. Run:"
  echo "  cd $preview_root/frontend && npm install"
  exit 1
fi

preview_password_hash="$($preview_python -m app.core.password_tool "$preview_password")"
preview_token_key="$($preview_python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
preview_session_secret="$($preview_python -c 'import secrets; print(secrets.token_urlsafe(48))')"

cleanup_preview() {
  if [[ -n "${preview_backend_pid:-}" ]]; then
    kill "$preview_backend_pid" 2>/dev/null || true
  fi
}
trap cleanup_preview EXIT INT TERM

(
  cd "$preview_root/backend"
  export COMMANDOS_OWNER_EMAIL="owner@example.com"
  export COMMANDOS_OWNER_PASSWORD_HASH="$preview_password_hash"
  export COMMANDOS_SESSION_SECRET="$preview_session_secret"
  export COMMANDOS_TOKEN_ENCRYPTION_KEY="$preview_token_key"
  export COMMANDOS_DATABASE_URL="sqlite:////tmp/commandos-preview.db"
  export COMMANDOS_AUTO_CREATE_SCHEMA="true"
  export COMMANDOS_FRONTEND_ORIGIN="$preview_frontend_url"
  export GOOGLE_CLIENT_ID="preview-client"
  export GOOGLE_CLIENT_SECRET="preview-secret"
  export GOOGLE_REDIRECT_URI="$preview_backend_url/api/youtube/callback"
  exec "$preview_uvicorn" app.main:app --host 127.0.0.1 --port "$preview_backend_port"
) &
preview_backend_pid=$!

echo
echo "CommandOS preview"
echo "URL:      $preview_frontend_url"
echo "Email:    owner@example.com"
echo "Password: $preview_password"
echo
echo "Keep this terminal open. Press Ctrl+C to stop the preview."
echo

cd "$preview_root/frontend"
exec npm run dev -- --config vite.preview.config.ts --host 127.0.0.1 --port "$preview_frontend_port" --strictPort
