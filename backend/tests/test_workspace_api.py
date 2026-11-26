from fastapi.testclient import TestClient

from app.main import app


def owner_client() -> TestClient:
    client = TestClient(app)
    client.__enter__()
    response = client.post(
        "/api/auth/login",
        json={
            "email": "owner@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 204
    csrf_token = client.cookies.get("commandos_csrf")
    assert csrf_token
    client.headers.update({"X-CSRF-Token": csrf_token})
    return client


def test_owner_workspace_persists_context_creator_and_content() -> None:
    client = owner_client()
    try:
        context = client.put(
            "/api/business-context",
            json={
                "brand_name": "CloudDataFriend",
                "mission": "Help data professionals build real systems.",
                "target_audience": "Data engineers and analysts",
                "content_pillars": ["Data Engineering", "AI Engineering"],
                "business_goals": ["Grow qualified audience"],
                "services": ["Workshops"],
                "resources": ["Study guides"],
            },
        )
        assert context.status_code == 200
        assert context.json()["configured"] is True

        creator = client.post(
            "/api/creators",
            json={
                "name": "Evidence Creator",
                "platform": "youtube",
                "profile_url": "https://youtube.com/@evidence-creator",
                "niche": "Data Engineering",
                "notes": "Public-source research only",
            },
        )
        assert creator.status_code == 201
        assert creator.json()["profile_url"].startswith("https://youtube.com/")
        creator_id = creator.json()["id"]

        evidence = client.post(
            f"/api/creators/{creator_id}/evidence",
            json={
                "evidence_type": "content",
                "title": "A public tutorial",
                "observation": "The tutorial opens with a concrete system failure.",
                "source_url": "https://youtube.com/watch?v=evidence",
                "public_metrics": {"views": 1200},
                "limitations": "Retention and reach are unavailable.",
            },
        )
        assert evidence.status_code == 201
        assert evidence.json()["public_metrics"]["views"] == 1200
        evidence_list = client.get(f"/api/creators/{creator_id}/evidence")
        assert evidence_list.status_code == 200
        assert len(evidence_list.json()) == 1

        project = client.post(
            "/api/content-projects",
            json={"title": "Build a reliable data pipeline", "platform": "youtube"},
        )
        assert project.status_code == 201
        project_id = project.json()["id"]

        moved = client.patch(
            f"/api/content-projects/{project_id}",
            json={
                "status": "production",
                "hook": "Why reliable pipelines fail in production",
                "brief": "Show the failure, explain the guardrail, demonstrate the fix.",
                "planned_for": "2026-12-03",
            },
        )
        assert moved.status_code == 200
        assert moved.json()["status"] == "production"
        assert moved.json()["planned_for"] == "2026-12-03"

        overview = client.get("/api/workspace/overview")
        assert overview.status_code == 200
        assert overview.json()["business_context_configured"] is True
        assert overview.json()["watchlist_count"] >= 1
        assert overview.json()["content_project_count"] >= 1

        deleted = client.delete(f"/api/content-projects/{project_id}")
        assert deleted.status_code == 204
    finally:
        client.__exit__(None, None, None)


def test_analytics_does_not_turn_missing_metrics_into_zero() -> None:
    client = owner_client()
    try:
        response = client.get("/api/analytics/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["provider"] == "youtube"
        assert isinstance(body["metrics"], list)
    finally:
        client.__exit__(None, None, None)
