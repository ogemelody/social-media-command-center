from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import TokenCipher
from app.db.session import SessionLocal, create_schema
from app.models.entities import (
    ContentItem,
    MetricObservation,
    ProviderConnection,
    SyncRun,
    SyncStatus,
)
from app.providers.youtube.client import MetricValue, OAuthTokens, YouTubeChannel, YouTubeVideo
from app.services.youtube_sync import YouTubeSyncService


class FakeYouTubeClient:
    async def refresh(self, refresh_token: str) -> OAuthTokens:
        return OAuthTokens("refreshed", refresh_token, datetime.now(UTC) + timedelta(hours=1), [])

    async def channel(self, access_token: str) -> YouTubeChannel:
        return YouTubeChannel("channel-integration", "CloudDataFriend", "uploads")

    async def videos(self, access_token: str, playlist: str, limit: int) -> list[YouTubeVideo]:
        return [YouTubeVideo("video-integration", "Feature 001", datetime.now(UTC), 120)]

    async def analytics(
        self, access_token: str, start_date: date, end_date: date
    ) -> list[MetricValue]:
        return [MetricValue("video-integration", end_date, "views", "count", 0)]


@pytest.mark.asyncio
async def test_sync_is_idempotent_and_preserves_real_zero() -> None:
    create_schema()
    settings = get_settings()
    cipher = TokenCipher(settings.token_encryption_key.get_secret_value())
    with SessionLocal() as session:
        connection = ProviderConnection(
            external_account_id="channel-integration",
            display_name="CloudDataFriend",
            encrypted_access_token=cipher.encrypt("access"),
            encrypted_refresh_token=cipher.encrypt("refresh"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(connection)
        session.commit()

        service = YouTubeSyncService(settings, session)
        service.client = FakeYouTubeClient()  # type: ignore[assignment]
        run = service.create_run(connection, "same-request")
        duplicate = service.create_run(connection, "same-request")

        assert duplicate.id == run.id

        await service.execute(run.id)
        session.expire_all()

        completed = session.get(SyncRun, run.id)
        observation = session.scalar(select(MetricObservation))
        content_count = session.scalar(select(func.count()).select_from(ContentItem))

        assert completed is not None and completed.status == SyncStatus.SUCCEEDED
        assert content_count == 1
        assert observation is not None
        assert observation.value == 0
        assert observation.availability == "available"
