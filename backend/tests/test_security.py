import pytest
from cryptography.fernet import Fernet

from app.core.security import (
    SecurityError,
    SessionSigner,
    TokenCipher,
    create_pkce_pair,
    generate_password_hash,
    verify_password,
)


def test_password_hash_accepts_only_matching_password() -> None:
    encoded = generate_password_hash("correct-horse-battery-staple", salt=b"0123456789abcdef")

    assert verify_password("correct-horse-battery-staple", encoded)
    assert not verify_password("wrong-password", encoded)
    assert not verify_password("correct-horse-battery-staple", "not-a-supported-hash")


def test_session_signer_rejects_tampering_and_expiry() -> None:
    signer = SessionSigner("a" * 32)
    token = signer.create("owner@example.com", ttl_seconds=60, now=1_000)

    assert signer.verify(token, now=1_001).email == "owner@example.com"
    with pytest.raises(SecurityError):
        signer.verify(f"{token}x", now=1_001)
    with pytest.raises(SecurityError):
        signer.verify(token, now=1_060)


def test_token_cipher_does_not_store_plaintext() -> None:
    cipher = TokenCipher(Fernet.generate_key().decode())
    encrypted = cipher.encrypt("provider-secret")

    assert encrypted != "provider-secret"
    assert "provider-secret" not in encrypted
    assert cipher.decrypt(encrypted) == "provider-secret"


def test_pkce_verifier_and_challenge_are_distinct_and_random() -> None:
    verifier_one, challenge_one = create_pkce_pair()
    verifier_two, challenge_two = create_pkce_pair()

    assert verifier_one != challenge_one
    assert verifier_one != verifier_two
    assert challenge_one != challenge_two
    assert "=" not in challenge_one
