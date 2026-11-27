from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.entities import ContentItem, MetricObservation, ProviderConnection, SyncRun
from app.services.analytics import dashboard, resolve_date_range
from app.services.scheduler import sync_is_due


def add_observation(
    session: Session,
    *,
    connection: ProviderConnection,
    content: ContentItem,
    run: SyncRun,
    key: str,
    value: float,
    day: date,
    unit: str = "count",
) -> None:
    session.add(
        MetricObservation(
            connection_id=connection.id,
            content_id=content.id,
            sync_run_id=run.id,
            metric_key=key,
            unit=unit,
            value=value,
            period_start=day,
            period_end=day,
        )
    )


def test_dashboard_aggregates_period_and_ranks_content(db_session: Session) -> None:
    connection = ProviderConnection(
        external_account_id="dashboard-channel",
        display_name="CloudDataFriend",
    )
    db_session.add(connection)
    db_session.flush()
    run = SyncRun(connection_id=connection.id, idempotency_key="dashboard-run")
    first = ContentItem(
        connection_id=connection.id,
        provider_content_id="dashboard-video-1",
        title="First video",
        url="https://youtube.com/watch?v=dashboard-video-1",
        published_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    second = ContentItem(
        connection_id=connection.id,
        provider_content_id="dashboard-video-2",
        title="Second video",
        url="https://youtube.com/watch?v=dashboard-video-2",
        published_at=datetime(2025, 1, 2, tzinfo=UTC),
    )
    db_session.add_all([run, first, second])
    db_session.flush()
    day = date(2025, 1, 3)
    add_observation(
        db_session, connection=connection, content=first, run=run, key="views", value=100, day=day
    )
    add_observation(
        db_session,
        connection=connection,
        content=first,
        run=run,
        key="estimatedMinutesWatched",
        value=200,
        day=day,
        unit="minutes",
    )
    add_observation(
        db_session, connection=connection, content=second, run=run, key="views", value=50, day=day
    )
    add_observation(
        db_session,
        connection=connection,
        content=second,
        run=run,
        key="estimatedMinutesWatched",
        value=50,
        day=day,
        unit="minutes",
    )
    db_session.commit()

    result = dashboard(db_session, day, day)
    metrics = {item["key"]: item for item in result["metrics"]}

    assert metrics["views"]["value"] == 150
    assert metrics["estimatedMinutesWatched"]["value"] == 250
    assert metrics["averageViewDuration"]["value"] == 100
    assert result["views_trend"][0]["value"] == 150
    assert result["top_content"][0]["title"] == "First video"
    assert result["top_content"][0]["views"] == 100
    assert metrics["comments"]["availability"] == "unavailable"
    assert metrics["comments"]["value"] is None

    zero_day = date(2025, 1, 4)
    add_observation(
        db_session,
        connection=connection,
        content=first,
        run=run,
        key="views",
        value=0,
        day=zero_day,
    )
    db_session.commit()
    zero_result = dashboard(db_session, zero_day, zero_day)
    zero_metrics = {item["key"]: item for item in zero_result["metrics"]}
    assert zero_metrics["views"]["availability"] == "available"
    assert zero_metrics["views"]["value"] == 0


def test_date_ranges_and_scheduler_due_logic() -> None:
    start, end = resolve_date_range("7d", None, None, today=date(2026, 11, 26))
    assert start == date(2026, 11, 20)
    assert end == date(2026, 11, 26)

    now = datetime(2026, 11, 26, 12, tzinfo=UTC)
    assert sync_is_due(None, now=now, interval_hours=24)
    assert sync_is_due(now - timedelta(hours=25), now=now, interval_hours=24)
    assert not sync_is_due(now - timedelta(hours=23), now=now, interval_hours=24)
