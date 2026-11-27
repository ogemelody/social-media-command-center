from fastapi.testclient import TestClient

from app.main import app


def test_protected_route_requires_owner_session() -> None:
    with TestClient(app) as client:
        response = client.get("/api/youtube/connection")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}

    with TestClient(app) as client:
        callback = client.get("/api/youtube/callback?code=fake&state=fake")

    assert callback.status_code == 401


def test_owner_can_login_and_start_read_only_oauth() -> None:
    with TestClient(app) as client:
        invalid = client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "wrong-password"},
        )
        assert invalid.status_code == 401

        login = client.post(
            "/api/auth/login",
            json={
                "email": "owner@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
        assert login.status_code == 204
        assert login.cookies.get("commandos_session")

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json() == {"email": "owner@example.com"}

        csrf_token = client.cookies.get("commandos_csrf")
        assert csrf_token
        rejected = client.post("/api/youtube/connect")
        assert rejected.status_code == 403

        client.headers.update({"X-CSRF-Token": csrf_token})
        connect = client.post("/api/youtube/connect")
        assert connect.status_code == 200
        url = connect.json()["authorization_url"]
        assert "youtube.readonly" in url
        assert "yt-analytics.readonly" in url
        assert "code_challenge=" in url
        assert "youtube.upload" not in url
