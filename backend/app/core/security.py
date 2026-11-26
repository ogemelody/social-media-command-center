import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken


class SecurityError(ValueError):
    """Raised when a signed or encrypted value cannot be trusted."""


def generate_password_hash(password: str, *, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=actual_salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${_b64_encode(actual_salt)}${_b64_encode(digest)}"


def verify_password(candidate: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$", maxsplit=5)
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            candidate.encode(),
            salt=_b64_decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        return hmac.compare_digest(digest, _b64_decode(expected))
    except (ValueError, TypeError):
        return False


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class SessionClaims:
    email: str
    expires_at: int


class SessionSigner:
    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def create(self, email: str, ttl_seconds: int, now: int | None = None) -> str:
        issued_at = int(time.time() if now is None else now)
        payload = {"email": email, "iat": issued_at, "exp": issued_at + ttl_seconds}
        encoded = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
        signature = _b64_encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
        return f"{encoded}.{signature}"

    def verify(self, token: str, now: int | None = None) -> SessionClaims:
        try:
            encoded, signature = token.split(".", maxsplit=1)
            expected = hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64_decode(signature)):
                raise SecurityError("Invalid session")
            payload = json.loads(_b64_decode(encoded))
            expires_at = int(payload["exp"])
            email = str(payload["email"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise SecurityError("Invalid session") from exc
        if expires_at <= int(time.time() if now is None else now):
            raise SecurityError("Session expired")
        return SessionClaims(email=email, expires_at=expires_at)


class TokenCipher:
    def __init__(self, key: str) -> None:
        try:
            self._cipher = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise SecurityError("Invalid token encryption key") from exc

    def encrypt(self, value: str) -> str:
        return self._cipher.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._cipher.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise SecurityError("Unable to decrypt provider credential") from exc


def create_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = _b64_encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def create_oauth_state() -> str:
    return secrets.token_urlsafe(32)
