from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ContentItem, MetricObservation, ProviderConnection

DASHBOARD_METRICS: tuple[tuple[str, str], ...] = (
    ("views", "count"),
    ("estimatedMinutesWatched", "minutes"),
    ("averageViewDuration", "seconds"),
    ("subscribersGained", "count"),
    ("likes", "count"),
    ("comments", "count"),
)


def utc_value(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def resolve_date_range(
    period: str,
    start_date: date | None,
    end_date: date | None,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    actual_today = today or date.today()
    preset_days = {"7d": 7, "28d": 28, "90d": 90}
    if period in preset_days:
        actual_end = end_date or actual_today
        return actual_end - timedelta(days=preset_days[period] - 1), actual_end
    if period != "custom" or start_date is None or end_date is None:
        raise ValueError("Custom ranges require both a start date and an end date")
    if start_date > end_date:
        raise ValueError("The start date must be on or before the end date")
    if (end_date - start_date).days > 365:
        raise ValueError("Analytics ranges cannot exceed 366 days")
    return start_date, end_date


def _metric(
    key: str,
    unit: str,
    values: dict[str, float],
    present: set[str],
) -> dict[str, object]:
    if key not in present:
        return {
            "key": key,
            "value": None,
            "unit": unit,
            "availability": "unavailable",
            "reason": "No observation is available for this period",
        }
    return {
        "key": key,
        "value": values.get(key, 0.0),
        "unit": unit,
        "availability": "available",
        "reason": None,
    }


def dashboard(
    session: Session,
    start_date: date,
    end_date: date,
) -> dict[str, object]:
    connection = session.scalar(
        select(ProviderConnection).where(ProviderConnection.provider == "youtube")
    )
    observations = session.scalars(
        select(MetricObservation).where(
            MetricObservation.provider == "youtube",
            MetricObservation.availability == "available",
            MetricObservation.value.is_not(None),
            MetricObservation.period_end >= start_date,
            MetricObservation.period_end <= end_date,
        )
    ).all()

    totals: dict[str, float] = defaultdict(float)
    present: set[str] = set()
    daily_views: dict[date, float] = defaultdict(float)
    daily_present: set[date] = set()
    content_metrics: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    content_present: dict[str, set[str]] = defaultdict(set)

    for observation in observations:
        key = observation.metric_key
        value = float(observation.value or 0)
        if key != "averageViewDuration":
            totals[key] += value
            present.add(key)
        if key == "views":
            daily_views[observation.period_end] += value
            daily_present.add(observation.period_end)
        if observation.content_id and key != "averageViewDuration":
            content_metrics[observation.content_id][key] += value
            content_present[observation.content_id].add(key)

    if "views" in present and "estimatedMinutesWatched" in present and totals["views"] > 0:
        totals["averageViewDuration"] = totals["estimatedMinutesWatched"] * 60 / totals["views"]
        present.add("averageViewDuration")

    metrics = [_metric(key, unit, totals, present) for key, unit in DASHBOARD_METRICS]

    trend = []
    cursor = start_date
    while cursor <= end_date:
        trend.append(
            {
                "date": cursor,
                "value": daily_views.get(cursor) if cursor in daily_present else None,
                "unit": "count",
                "availability": "available" if cursor in daily_present else "unavailable",
            }
        )
        cursor += timedelta(days=1)

    content_ids = list(content_metrics)
    content_by_id = (
        {
            item.id: item
            for item in session.scalars(
                select(ContentItem).where(ContentItem.id.in_(content_ids))
            ).all()
        }
        if content_ids
        else {}
    )
    ranked_ids = sorted(
        content_ids,
        key=lambda content_id: content_metrics[content_id].get("views", -1),
        reverse=True,
    )
    top_content = []
    for content_id in ranked_ids[:10]:
        content = content_by_id.get(content_id)
        if not content or "views" not in content_present[content_id]:
            continue
        values = content_metrics[content_id]
        video_views = values.get("views", 0)
        average_duration = None
        if "estimatedMinutesWatched" in content_present[content_id] and video_views > 0:
            average_duration = values.get("estimatedMinutesWatched", 0) * 60 / video_views
        top_content.append(
            {
                "id": content.id,
                "title": content.title,
                "url": content.url,
                "published_at": utc_value(content.published_at),
                "views": video_views,
                "watch_minutes": values.get("estimatedMinutesWatched")
                if "estimatedMinutesWatched" in content_present[content_id]
                else None,
                "average_view_duration_seconds": average_duration,
                "likes": values.get("likes") if "likes" in content_present[content_id] else None,
                "comments": values.get("comments")
                if "comments" in content_present[content_id]
                else None,
            }
        )

    freshness = max((utc_value(item.retrieved_at) for item in observations), default=None)
    return {
        "provider": "youtube",
        "source": "Official YouTube APIs",
        "connected": bool(connection and connection.status == "active"),
        "channel_name": connection.display_name if connection else None,
        "freshness": freshness,
        "range": {"start": start_date, "end": end_date},
        "metrics": metrics,
        "views_trend": trend,
        "top_content": top_content,
    }
