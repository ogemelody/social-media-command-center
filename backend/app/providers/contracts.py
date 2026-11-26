from dataclasses import asdict, dataclass
from typing import Protocol

from app.models.entities import ProviderConnection, SyncRun


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    unit: str
    aggregation: str
    scope: str
    description: str

    def serialize(self) -> dict[str, str]:
        return asdict(self)


OWNED_ANALYTICS_METRICS = (
    MetricDefinition(
        "views",
        "Views",
        "count",
        "sum",
        "channel_and_content",
        "Valid video views reported by the provider.",
    ),
    MetricDefinition(
        "estimatedMinutesWatched",
        "Watch time",
        "minutes",
        "sum",
        "channel_and_content",
        "Estimated minutes watched for the selected reporting period.",
    ),
    MetricDefinition(
        "averageViewDuration",
        "Average view duration",
        "seconds",
        "provider_calculated",
        "channel_and_content",
        "Provider-calculated average duration watched.",
    ),
    MetricDefinition(
        "subscribersGained",
        "Subscribers gained",
        "count",
        "sum",
        "channel",
        "Subscribers gained during the selected reporting period.",
    ),
    MetricDefinition(
        "likes",
        "Likes",
        "count",
        "sum",
        "content",
        "Public or authorized likes reported by the provider.",
    ),
    MetricDefinition(
        "comments", "Comments", "count", "sum", "content", "Comments reported by the provider."
    ),
    MetricDefinition(
        "shares",
        "Shares",
        "count",
        "sum",
        "content",
        "Authorized share count when the provider makes it available.",
    ),
)


class AnalyticsProvider(Protocol):
    """Provider-neutral contract used by synchronization orchestration."""

    provider_name: str

    async def synchronize(self, connection: ProviderConnection, run: SyncRun) -> None: ...
