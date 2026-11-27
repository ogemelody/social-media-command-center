from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.entities import CreatorVideo, CreatorVideoComment


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
                "niche": "Data Engineering",
                "notes": "Public-source research only",
                "profiles": [
                    {
                        "platform": "youtube",
                        "profile_url": "https://youtube.com/@evidence-creator",
                    },
                    {
                        "platform": "instagram",
                        "profile_url": "https://instagram.com/evidence-creator",
                    },
                ],
            },
        )
        assert creator.status_code == 201
        assert {profile["platform"] for profile in creator.json()["profiles"]} == {
            "youtube",
            "instagram",
        }
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


def test_creator_identity_cannot_be_duplicated_across_platforms() -> None:
    client = owner_client()
    try:
        first = client.post(
            "/api/creators",
            json={
                "name": "Keerti Purswani",
                "niche": "Data Engineering",
                "notes": "Clear teaching style",
                "profiles": [
                    {
                        "platform": "youtube",
                        "profile_url": "https://youtube.com/@keertipurswani",
                    }
                ],
            },
        )
        assert first.status_code == 201

        duplicate = client.post(
            "/api/creators",
            json={
                "name": "keerti.purswani",
                "niche": "AI Engineering and AI Agents",
                "notes": "Instagram profile",
                "profiles": [
                    {
                        "platform": "instagram",
                        "profile_url": "https://instagram.com/keerti.purswani",
                    }
                ],
            },
        )
        assert duplicate.status_code == 409
        assert "existing profile" in duplicate.json()["detail"]

        updated = client.patch(
            f"/api/creators/{first.json()['id']}",
            json={
                "profiles": [
                    {
                        "platform": "youtube",
                        "profile_url": "https://youtube.com/@keertipurswani",
                    },
                    {
                        "platform": "instagram",
                        "profile_url": "https://instagram.com/keerti.purswani",
                    },
                ]
            },
        )
        assert updated.status_code == 200
        assert len(updated.json()["profiles"]) == 2
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


def test_custom_analytics_range_requires_both_dates() -> None:
    client = owner_client()
    try:
        response = client.get("/api/analytics/dashboard?range=custom&start_date=2026-11-01")
        assert response.status_code == 422
        assert (
            response.json()["detail"] == "Custom ranges require both a start date and an end date"
        )
    finally:
        client.__exit__(None, None, None)


def test_creator_research_exposes_relative_performance_and_questions() -> None:
    client = owner_client()
    try:
        creator = client.post(
            "/api/creators",
            json={
                "name": "Research Contract Creator",
                "niche": "Data Engineering",
                "notes": "Research contract",
                "profiles": [
                    {
                        "platform": "youtube",
                        "profile_url": "https://youtube.com/@research-contract",
                    }
                ],
            },
        )
        assert creator.status_code == 201
        creator_id = creator.json()["id"]
        now = datetime.now(UTC)
        with SessionLocal() as session:
            videos = []
            for index, views in enumerate((100, 100, 300)):
                video = CreatorVideo(
                    creator_id=creator_id,
                    provider_video_id=f"research-video-{index}",
                    title=f"Research video {index}",
                    description="A public description",
                    source_url=f"https://youtube.com/watch?v=research-video-{index}",
                    published_at=now,
                    views=views,
                    likes=10,
                    comments_count=2,
                )
                session.add(video)
                session.flush()
                videos.append(video)
            session.add(
                CreatorVideoComment(
                    video_id=videos[-1].id,
                    provider_comment_id="research-question",
                    text="Can you show the architecture?",
                    author_name="Viewer",
                    like_count=4,
                    published_at=now,
                    source_url="https://youtube.com/watch?v=research-video-2&lc=research-question",
                )
            )
            session.commit()

        response = client.get(f"/api/creators/{creator_id}/youtube/research")
        assert response.status_code == 200
        body = response.json()
        assert body["baseline"] == {"metric": "views", "median": 100, "sample_size": 3}
        breakout = next(
            video for video in body["videos"] if video["public_metrics"]["views"] == 300
        )
        assert breakout["performance_label"] == "breakout"
        assert breakout["relative_view_ratio"] == 3.0
        assert breakout["audience_questions"][0]["text"] == "Can you show the architecture?"
        assert any("Spoken hooks" in limitation for limitation in body["limitations"])
    finally:
        client.__exit__(None, None, None)


def test_creator_refresh_requires_a_youtube_profile() -> None:
    client = owner_client()
    try:
        creator = client.post(
            "/api/creators",
            json={
                "name": "Instagram Only Research Creator",
                "niche": "Data Engineering",
                "profiles": [
                    {
                        "platform": "instagram",
                        "profile_url": "https://instagram.com/research-contract-only",
                    }
                ],
            },
        )
        assert creator.status_code == 201
        response = client.post(f"/api/creators/{creator.json()['id']}/youtube/refresh")
        assert response.status_code == 409
        assert "YouTube profile" in response.json()["detail"]
    finally:
        client.__exit__(None, None, None)
