import os

from cryptography.fernet import Fernet

from app.core.security import generate_password_hash

os.environ.setdefault("COMMANDOS_OWNER_EMAIL", "owner@example.com")
os.environ.setdefault(
    "COMMANDOS_OWNER_PASSWORD_HASH",
    generate_password_hash("correct-horse-battery-staple", salt=b"0123456789abcdef"),
)
os.environ.setdefault("COMMANDOS_SESSION_SECRET", "test-session-secret-with-at-least-32-characters")
os.environ.setdefault("COMMANDOS_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("COMMANDOS_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("COMMANDOS_AUTO_CREATE_SCHEMA", "true")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/youtube/callback")
