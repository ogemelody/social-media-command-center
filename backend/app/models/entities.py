from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ConnectionStatus(StrEnum):
    ACTIVE = "active"
    AUTHORIZATION_REQUIRED = "authorization_required"
    DISCONNECTED = "disconnected"


class SyncStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class Availability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_REQUESTED = "not_requested"
    DELAYED = "delayed"
    RESTRICTED = "restricted"
    ERROR = "error"


class ProviderConnection(Base):
    __tablename__ = "provider_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider: Mapped[str] = mapped_column(String(32), default="youtube")
    external_account_id: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=ConnectionStatus.ACTIVE)
    last_validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    content_items: Mapped[list["ContentItem"]] = relationship(cascade="all, delete-orphan")


class OAuthAttempt(Base):
    __tablename__ = "oauth_attempts"

    state: Mapped[str] = mapped_column(String(255), primary_key=True)
    pkce_verifier: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = (UniqueConstraint("provider", "provider_content_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    connection_id: Mapped[str] = mapped_column(ForeignKey("provider_connections.id"))
    provider: Mapped[str] = mapped_column(String(32), default="youtube")
    provider_content_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(32), default="video")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (UniqueConstraint("connection_id", "idempotency_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    connection_id: Mapped[str] = mapped_column(ForeignKey("provider_connections.id"))
    idempotency_key: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default=SyncStatus.QUEUED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_read: Mapped[int] = mapped_column(default=0)
    records_written: Mapped[int] = mapped_column(default=0)
    records_rejected: Mapped[int] = mapped_column(default=0)
    retry_count: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MetricObservation(Base):
    __tablename__ = "metric_observations"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "content_id",
            "metric_key",
            "period_start",
            "period_end",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    connection_id: Mapped[str] = mapped_column(ForeignKey("provider_connections.id"))
    content_id: Mapped[str | None] = mapped_column(ForeignKey("content_items.id"), nullable=True)
    sync_run_id: Mapped[str] = mapped_column(ForeignKey("sync_runs.id"))
    provider: Mapped[str] = mapped_column(String(32), default="youtube")
    metric_key: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(32))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability: Mapped[str] = mapped_column(String(32), default=Availability.AVAILABLE)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BusinessContext(Base):
    __tablename__ = "business_context"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="owner")
    brand_name: Mapped[str] = mapped_column(String(255), default="CloudDataFriend")
    mission: Mapped[str] = mapped_column(Text, default="")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    content_pillars: Mapped[list[str]] = mapped_column(JSON, default=list)
    business_goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    services: Mapped[list[str]] = mapped_column(JSON, default=list)
    resources: Mapped[list[str]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CreatorWatchlistItem(Base):
    __tablename__ = "creator_watchlist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    niche: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str] = mapped_column(Text, default="")
    evidence_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidence: Mapped[list["CreatorEvidence"]] = relationship(
        cascade="all, delete-orphan", back_populates="creator"
    )
    profiles: Mapped[list["CreatorPlatformProfile"]] = relationship(
        cascade="all, delete-orphan", back_populates="creator"
    )
    research_runs: Mapped[list["CreatorResearchRun"]] = relationship(
        cascade="all, delete-orphan", back_populates="creator"
    )
    videos: Mapped[list["CreatorVideo"]] = relationship(
        cascade="all, delete-orphan", back_populates="creator"
    )


class CreatorPlatformProfile(Base):
    __tablename__ = "creator_platform_profiles"
    __table_args__ = (
        UniqueConstraint("creator_id", "platform"),
        UniqueConstraint("platform", "profile_url"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator_watchlist_items.id"))
    platform: Mapped[str] = mapped_column(String(32))
    profile_url: Mapped[str] = mapped_column(Text)
    provider_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploads_playlist_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    creator: Mapped[CreatorWatchlistItem] = relationship(back_populates="profiles")


class CreatorResearchRun(Base):
    __tablename__ = "creator_research_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator_watchlist_items.id"))
    provider: Mapped[str] = mapped_column(String(32), default="youtube")
    status: Mapped[str] = mapped_column(String(32), default="running")
    estimated_quota_units: Mapped[int] = mapped_column(default=0)
    records_read: Mapped[int] = mapped_column(default=0)
    records_written: Mapped[int] = mapped_column(default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped[CreatorWatchlistItem] = relationship(back_populates="research_runs")


class CreatorVideo(Base):
    __tablename__ = "creator_videos"
    __table_args__ = (UniqueConstraint("provider", "provider_video_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator_watchlist_items.id"))
    provider: Mapped[str] = mapped_column(String(32), default="youtube")
    provider_video_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    views: Mapped[int | None] = mapped_column(nullable=True)
    likes: Mapped[int | None] = mapped_column(nullable=True)
    comments_count: Mapped[int | None] = mapped_column(nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    creator: Mapped[CreatorWatchlistItem] = relationship(back_populates="videos")
    comments: Mapped[list["CreatorVideoComment"]] = relationship(
        cascade="all, delete-orphan", back_populates="video"
    )


class CreatorVideoComment(Base):
    __tablename__ = "creator_video_comments"
    __table_args__ = (UniqueConstraint("provider", "provider_comment_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    video_id: Mapped[str] = mapped_column(ForeignKey("creator_videos.id"))
    provider: Mapped[str] = mapped_column(String(32), default="youtube")
    provider_comment_id: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    like_count: Mapped[int | None] = mapped_column(nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    video: Mapped[CreatorVideo] = relationship(back_populates="comments")


class CreatorEvidence(Base):
    __tablename__ = "creator_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator_watchlist_items.id"))
    evidence_type: Mapped[str] = mapped_column(String(32), default="content")
    title: Mapped[str] = mapped_column(Text)
    observation: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    public_metrics: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    limitations: Mapped[str] = mapped_column(Text, default="")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    creator: Mapped[CreatorWatchlistItem] = relationship(back_populates="evidence")


class ContentProject(Base):
    __tablename__ = "content_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="idea")
    platform: Mapped[str] = mapped_column(String(32), default="youtube")
    content_type: Mapped[str] = mapped_column(String(32), default="video")
    pillar: Mapped[str] = mapped_column(String(100), default="")
    hook: Mapped[str] = mapped_column(Text, default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    published_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
