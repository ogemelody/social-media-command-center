from datetime import date

from app.services.youtube_sync import make_idempotency_key


def test_idempotency_key_is_stable_for_same_sync_window() -> None:
    first = make_idempotency_key("connection-1", date(2026, 9, 1), date(2026, 11, 25), "request-1")
    second = make_idempotency_key("connection-1", date(2026, 9, 1), date(2026, 11, 25), "request-1")
    different = make_idempotency_key(
        "connection-1", date(2026, 9, 1), date(2026, 11, 25), "request-2"
    )

    assert first == second
    assert first != different
