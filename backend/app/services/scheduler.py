from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models.entities import ProviderConnection, SyncRun
from app.services.youtube_sync import YouTubeSyncService, run_sync_in_new_session

logger = logging.getLogger(__name__)


def sync_is_due(
    last_finished_at: datetime | None,
    *,
    now: datetime,
    interval_hours: int,
) -> bool:
    if last_finished_at is None:
        return True
    finished_at = (
        last_finished_at.replace(tzinfo=UTC)
        if last_finished_at.tzinfo is None
        else last_finished_at.astimezone(UTC)
    )
    return finished_at <= now - timedelta(hours=interval_hours)


def run_due_sync(settings: Settings) -> str | None:
    run_id: str | None = None
    with SessionLocal() as session:
        connection = session.scalar(
            select(ProviderConnection).where(
                ProviderConnection.provider == "youtube",
                ProviderConnection.status == "active",
            )
        )
        if not connection:
            return None
        service = YouTubeSyncService(settings, session)
        active = service.active_run(connection.id)
        if active:
            return active.id
        latest_success = session.scalar(
            select(SyncRun)
            .where(
                SyncRun.connection_id == connection.id,
                SyncRun.status.in_(["succeeded", "partial"]),
            )
            .order_by(SyncRun.finished_at.desc())
        )
        if not sync_is_due(
            latest_success.finished_at if latest_success else None,
            now=datetime.now(UTC),
            interval_hours=settings.youtube_sync_interval_hours,
        ):
            return None
        run = service.create_run(
            connection,
            request_key=f"scheduled:{datetime.now(UTC).date().isoformat()}",
        )
        run_id = run.id
    if run_id:
        run_sync_in_new_session(settings, run_id)
    return run_id


async def scheduled_sync_loop(settings: Settings, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(run_due_sync, settings)
        except Exception:
            logger.exception("Scheduled YouTube synchronization failed")
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=settings.youtube_scheduler_poll_seconds
            )
        except TimeoutError:
            continue
