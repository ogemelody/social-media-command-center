import asyncio
import hashlib
import secrets
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import TokenCipher
from app.db.session import SessionLocal
from app.models.entities import (
    Availability,
    ConnectionStatus,
    ContentItem,
    MetricObservation,
    ProviderConnection,
    SyncRun,
    SyncStatus,
)
from app.providers.youtube.client import YouTubeClient, YouTubeProviderError


def make_idempotency_key(
    connection_id: str, start_date: date, end_date: date, request_key: str = ""
) -> str:
    source = f"{connection_id}:{start_date.isoformat()}:{end_date.isoformat()}:{request_key}"
    return hashlib.sha256(source.encode()).hexdigest()


class YouTubeSyncService:
    def __init__(self, settings: Settings, session: Session) -> None:
        self.settings = settings
        self.session = session
        self.cipher = TokenCipher(settings.token_encryption_key.get_secret_value())
        self.client = YouTubeClient(
            settings.google_client_id,
            settings.google_client_secret.get_secret_value(),
            settings.google_redirect_uri,
        )

    def active_run(self, connection_id: str) -> SyncRun | None:
        return self.session.scalar(
            select(SyncRun)
            .where(
                SyncRun.connection_id == connection_id,
                SyncRun.status.in_([SyncStatus.QUEUED, SyncStatus.RUNNING]),
            )
            .order_by(SyncRun.created_at.desc())
        )

    def create_run(self, connection: ProviderConnection, request_key: str | None = None) -> SyncRun:
        end_date = date.today()
        start_date = end_date - timedelta(days=self.settings.youtube_initial_history_days - 1)
        key = make_idempotency_key(
            connection.id, start_date, end_date, request_key or secrets.token_urlsafe(16)
        )
        existing = self.session.scalar(
            select(SyncRun).where(
                SyncRun.connection_id == connection.id,
                SyncRun.idempotency_key == key,
            )
        )
        if existing:
            return existing
        run = SyncRun(connection_id=connection.id, idempotency_key=key)
        self.session.add(run)
        self.session.commit()
        return run

    async def execute(self, run_id: str) -> None:
        run = self.session.get(SyncRun, run_id)
        if not run:
            return
        connection = self.session.get(ProviderConnection, run.connection_id)
        if not connection or connection.status != ConnectionStatus.ACTIVE:
            run.status = SyncStatus.FAILED
            run.error_code = "connection_inactive"
            run.error_summary = "The YouTube connection is not active"
            run.finished_at = datetime.now(UTC)
            self.session.commit()
            return

        run.status = SyncStatus.RUNNING
        run.started_at = datetime.now(UTC)
        self.session.commit()

        try:
            access_token = await self._valid_access_token(connection)
            channel = await self.client.channel(access_token)
            videos = await self.client.videos(
                access_token, channel.uploads_playlist_id, self.settings.youtube_max_videos
            )
            end_date = date.today()
            start_date = end_date - timedelta(days=self.settings.youtube_initial_history_days - 1)
            metrics = await self.client.analytics(
                access_token,
                start_date,
                end_date,
                [video.video_id for video in videos],
            )
            run.records_read = len(videos) + len(metrics)

            content_by_provider_id: dict[str, ContentItem] = {}
            for video in videos:
                content = self.session.scalar(
                    select(ContentItem).where(
                        ContentItem.provider == "youtube",
                        ContentItem.provider_content_id == video.video_id,
                    )
                )
                if not content:
                    content = ContentItem(
                        connection_id=connection.id,
                        provider_content_id=video.video_id,
                        title=video.title,
                        url=f"https://www.youtube.com/watch?v={video.video_id}",
                        published_at=video.published_at,
                        duration_seconds=video.duration_seconds,
                    )
                    self.session.add(content)
                    self.session.flush()
                    run.records_written += 1
                else:
                    content.title = video.title
                    content.published_at = video.published_at
                    content.duration_seconds = video.duration_seconds
                content_by_provider_id[video.video_id] = content

            for metric in metrics:
                content = content_by_provider_id.get(metric.video_id)
                if not content:
                    run.records_rejected += 1
                    continue
                observation = self.session.scalar(
                    select(MetricObservation).where(
                        MetricObservation.connection_id == connection.id,
                        MetricObservation.content_id == content.id,
                        MetricObservation.metric_key == metric.metric_key,
                        MetricObservation.period_start == metric.day,
                        MetricObservation.period_end == metric.day,
                    )
                )
                if not observation:
                    observation = MetricObservation(
                        connection_id=connection.id,
                        content_id=content.id,
                        sync_run_id=run.id,
                        metric_key=metric.metric_key,
                        unit=metric.unit,
                        period_start=metric.day,
                        period_end=metric.day,
                        value=metric.value,
                        availability=Availability.AVAILABLE,
                    )
                    self.session.add(observation)
                    run.records_written += 1
                else:
                    observation.value = metric.value
                    observation.sync_run_id = run.id
                    observation.retrieved_at = datetime.now(UTC)

            run.status = SyncStatus.PARTIAL if run.records_rejected else SyncStatus.SUCCEEDED
            run.finished_at = datetime.now(UTC)
            self.session.commit()
        except YouTubeProviderError as exc:
            self.session.rollback()
            run = self.session.get(SyncRun, run_id)
            connection = self.session.get(ProviderConnection, run.connection_id) if run else None
            if run:
                run.status = SyncStatus.FAILED
                run.error_code = exc.code
                run.error_summary = str(exc)[:500]
                run.finished_at = datetime.now(UTC)
            if connection and exc.code == "authorization_required":
                connection.status = ConnectionStatus.AUTHORIZATION_REQUIRED
            self.session.commit()
        except Exception:
            self.session.rollback()
            run = self.session.get(SyncRun, run_id)
            if run:
                run.status = SyncStatus.FAILED
                run.error_code = "internal_error"
                run.error_summary = "The synchronization failed unexpectedly"
                run.finished_at = datetime.now(UTC)
                self.session.commit()

    async def _valid_access_token(self, connection: ProviderConnection) -> str:
        if not connection.encrypted_access_token:
            raise YouTubeProviderError("authorization_required", "YouTube must be reconnected")
        access_token = self.cipher.decrypt(connection.encrypted_access_token)
        now = datetime.now(UTC)
        expires_at = connection.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if not expires_at or expires_at > now + timedelta(minutes=2):
            return access_token
        if not connection.encrypted_refresh_token:
            raise YouTubeProviderError("authorization_required", "YouTube must be reconnected")
        refreshed = await self.client.refresh(
            self.cipher.decrypt(connection.encrypted_refresh_token)
        )
        connection.encrypted_access_token = self.cipher.encrypt(refreshed.access_token)
        connection.expires_at = refreshed.expires_at
        connection.last_validated_at = now
        self.session.commit()
        return refreshed.access_token

    async def disconnect(self, connection: ProviderConnection) -> bool:
        revoked = False
        if connection.encrypted_access_token:
            access_token = self.cipher.decrypt(connection.encrypted_access_token)
            revoked = await self.client.revoke(access_token)
        connection.status = ConnectionStatus.DISCONNECTED
        connection.encrypted_access_token = None
        connection.encrypted_refresh_token = None
        self.session.execute(
            delete(MetricObservation).where(MetricObservation.connection_id == connection.id)
        )
        self.session.execute(delete(ContentItem).where(ContentItem.connection_id == connection.id))
        self.session.commit()
        return revoked


def run_sync_in_new_session(settings: Settings, run_id: str) -> None:
    with SessionLocal() as session:
        asyncio.run(YouTubeSyncService(settings, session).execute(run_id))
