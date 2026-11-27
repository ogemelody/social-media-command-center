import asyncio
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.entities import (
    CreatorPlatformProfile,
    CreatorVideo,
    CreatorVideoComment,
    CreatorWatchlistItem,
    ProviderConnection,
)
from app.providers.youtube.client import (
    YouTubeChannel,
    YouTubeProviderError,
    YouTubePublicComment,
    YouTubePublicVideo,
)
from app.services.creator_research import CreatorResearchService
from app.services.youtube_sync import YouTubeSyncService


class FakeCreatorYouTubeClient:
    async def public_channel(self, _token: str, _url: str) -> YouTubeChannel:
        return YouTubeChannel("creator-channel", "Creator", "creator-uploads")

    async def public_videos(
        self, _token: str, _playlist: str, _limit: int
    ) -> list[YouTubePublicVideo]:
        now = datetime.now(UTC)
        return [
            YouTubePublicVideo(
                video_id=f"controlled-video-{index}",
                title=f"Video {index}",
                description="Public description",
                published_at=now,
                duration_seconds=120,
                thumbnail_url=None,
                views=100 + index,
                likes=10,
                comments=1,
            )
            for index in range(6)
        ]

    async def public_comments(
        self, _token: str, video_id: str, _limit: int
    ) -> list[YouTubePublicComment]:
        return [
            YouTubePublicComment(
                comment_id=f"question-{video_id}",
                text="How did you build this?",
                author_name="Viewer",
                like_count=2,
                published_at=datetime.now(UTC),
            )
        ]


def test_creator_research_is_bounded_and_idempotent(db_session, monkeypatch) -> None:
    async def token(_service, _connection) -> str:
        return "read-only-token"

    monkeypatch.setattr(YouTubeSyncService, "valid_access_token", token)
    creator = CreatorWatchlistItem(
        name="Controlled Research Creator",
        niche="Data Engineering",
        profiles=[
            CreatorPlatformProfile(
                platform="youtube", profile_url="https://youtube.com/@controlled-research"
            )
        ],
    )
    db_session.add(creator)
    if not db_session.scalar(
        select(ProviderConnection).where(ProviderConnection.provider == "youtube")
    ):
        db_session.add(
            ProviderConnection(
                provider="youtube",
                external_account_id="owned-channel-for-research",
                display_name="CloudDataFriend",
                status="active",
            )
        )
    db_session.commit()
    service = CreatorResearchService(get_settings(), db_session)
    service.client = FakeCreatorYouTubeClient()  # type: ignore[assignment]

    first = asyncio.run(service.refresh(creator))
    second = asyncio.run(service.refresh(creator))

    assert first.status == "succeeded"
    assert first.estimated_quota_units == 8
    assert second.estimated_quota_units == 7
    assert db_session.scalar(select(func.count(CreatorVideo.id))) == 6
    assert db_session.scalar(select(func.count(CreatorVideoComment.id))) == 5


def test_creator_research_explains_comment_permission_failure(db_session, monkeypatch) -> None:
    async def token(_service, _connection) -> str:
        return "read-only-token"

    class PermissionDeniedClient(FakeCreatorYouTubeClient):
        async def public_comments(self, _token: str, _video_id: str, _limit: int):
            raise YouTubeProviderError(
                "insufficient_permissions", "YouTube did not grant comment access"
            )

    monkeypatch.setattr(YouTubeSyncService, "valid_access_token", token)
    creator = CreatorWatchlistItem(
        name="Permission Test Creator",
        niche="Data Engineering",
        profiles=[
            CreatorPlatformProfile(
                platform="youtube", profile_url="https://youtube.com/@permission-test"
            )
        ],
    )
    db_session.add(creator)
    if not db_session.scalar(
        select(ProviderConnection).where(ProviderConnection.provider == "youtube")
    ):
        db_session.add(
            ProviderConnection(
                provider="youtube",
                external_account_id="owned-channel-for-research",
                display_name="CloudDataFriend",
                status="active",
            )
        )
    db_session.commit()
    service = CreatorResearchService(get_settings(), db_session)
    service.client = PermissionDeniedClient()  # type: ignore[assignment]

    run = asyncio.run(service.refresh(creator))

    assert run.status == "partial"
    assert run.error_summary == (
        "YouTube denied OAuth comment access. Configure a restricted "
        "YOUTUBE_API_KEY for public comment research."
    )
