#!/usr/bin/env python3
"""Configure local Google OAuth credentials without printing secrets."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet

EXPECTED_REDIRECT_URI = "http://127.0.0.1:8001/api/youtube/callback"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a downloaded Google OAuth client into CommandOS."
    )
    parser.add_argument("credentials_json", type=Path)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "backend" / ".env",
    )
    return parser.parse_args()


def quoted(value: str) -> str:
    return json.dumps(value)


def main() -> None:
    args = parse_args()
    if args.env_file.exists():
        raise SystemExit(
            f"Refusing to overwrite existing configuration: {args.env_file}"
        )

    payload = json.loads(args.credentials_json.read_text(encoding="utf-8"))
    client = payload.get("web")
    if not isinstance(client, dict):
        raise SystemExit("Expected credentials for a Google Web application.")

    client_id = client.get("client_id")
    client_secret = client.get("client_secret")
    redirect_uris = client.get("redirect_uris", [])
    if not isinstance(client_id, str) or not isinstance(client_secret, str):
        raise SystemExit("The credentials file is missing a client ID or secret.")
    if EXPECTED_REDIRECT_URI not in redirect_uris:
        raise SystemExit(
            "The Google OAuth client does not contain the expected redirect URI: "
            f"{EXPECTED_REDIRECT_URI}"
        )

    contents = "\n".join(
        (
            "# Local-only CommandOS secrets. This file is ignored by Git.",
            f"COMMANDOS_TOKEN_ENCRYPTION_KEY={quoted(Fernet.generate_key().decode())}",
            f"GOOGLE_CLIENT_ID={quoted(client_id)}",
            f"GOOGLE_CLIENT_SECRET={quoted(client_secret)}",
            f"GOOGLE_REDIRECT_URI={quoted(EXPECTED_REDIRECT_URI)}",
            "",
        )
    )
    args.env_file.parent.mkdir(parents=True, exist_ok=True)
    with args.env_file.open("x", encoding="utf-8") as env_file:
        env_file.write(contents)
    os.chmod(args.env_file, 0o600)
    print(f"Configured Google OAuth in {args.env_file}")
    print("No credential values were displayed.")


if __name__ == "__main__":
    main()
