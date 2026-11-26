import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CSRF_COOKIE, SESSION_COOKIE, require_csrf, require_owner
from app.core.config import Settings, get_settings
from app.core.security import (
    SessionSigner,
    TokenCipher,
    create_oauth_state,
    create_pkce_pair,
    verify_password,
)
from app.db.session import get_db
from app.models.entities import (
    BusinessContext,
    ContentItem,
    ContentProject,
    CreatorEvidence,
    CreatorWatchlistItem,
    MetricObservation,
    OAuthAttempt,
    ProviderConnection,
    SyncRun,
    utcnow,
)
from app.providers.contracts import OWNED_ANALYTICS_METRICS
from app.providers.youtube.client import YouTubeClient, YouTubeProviderError
from app.services.analytics import dashboard, resolve_date_range, utc_value
from app.services.youtube_sync import YouTubeSyncService, run_sync_in_new_session

router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class BusinessContextPayload(BaseModel):
    brand_name: str = Field(min_length=1, max_length=255)
    mission: str = Field(default="", max_length=2000)
    target_audience: str = Field(default="", max_length=2000)
    content_pillars: list[str] = Field(default_factory=list, max_length=20)
    business_goals: list[str] = Field(default_factory=list, max_length=20)
    services: list[str] = Field(default_factory=list, max_length=20)
    resources: list[str] = Field(default_factory=list, max_length=30)


class CreatorPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    platform: Literal["youtube", "instagram", "tiktok", "linkedin"]
    profile_url: AnyHttpUrl
    niche: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=4000)


class CreatorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    platform: Literal["youtube", "instagram", "tiktok", "linkedin"] | None = None
    profile_url: AnyHttpUrl | None = None
    niche: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=4000)


class CreatorEvidencePayload(BaseModel):
    evidence_type: Literal["content", "comment", "profile", "trend"] = "content"
    title: str = Field(min_length=1, max_length=500)
    observation: str = Field(min_length=1, max_length=4000)
    source_url: AnyHttpUrl
    public_metrics: dict[str, int | float | str | None] = Field(default_factory=dict)
    limitations: str = Field(min_length=1, max_length=2000)
    observed_at: datetime | None = None


class ContentProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    platform: Literal["youtube", "instagram", "tiktok", "linkedin"] = "youtube"
    content_type: str = Field(default="video", max_length=32)
    pillar: str = Field(default="", max_length=100)
    hook: str = Field(default="", max_length=2000)
    brief: str = Field(default="", max_length=8000)
    source_url: AnyHttpUrl | None = None
    planned_for: date | None = None


class ContentProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    status: Literal["idea", "brief", "production", "scheduled", "published"] | None = None
    platform: Literal["youtube", "instagram", "tiktok", "linkedin"] | None = None
    content_type: str | None = Field(default=None, max_length=32)
    pillar: str | None = Field(default=None, max_length=100)
    hook: str | None = Field(default=None, max_length=2000)
    brief: str | None = Field(default=None, max_length=8000)
    source_url: AnyHttpUrl | None = None
    planned_for: date | None = None
    published_url: AnyHttpUrl | None = None


@router.post("/auth/login", status_code=status.HTTP_204_NO_CONTENT)
def login(
    payload: LoginRequest, response: Response, settings: Settings = Depends(get_settings)
) -> None:
    valid_email = payload.email.lower() == settings.owner_email
    valid_password = verify_password(
        payload.password, settings.owner_password_hash.get_secret_value()
    )
    if not (valid_email and valid_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = SessionSigner(settings.session_secret.get_secret_value()).create(
        settings.owner_email, settings.session_ttl_seconds
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=settings.session_ttl_seconds,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, _=Depends(require_csrf)) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.get("/auth/me")
def me(claims=Depends(require_owner)) -> dict[str, str]:
    return {"email": claims.email}


@router.post("/youtube/connect")
def youtube_connect(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _=Depends(require_csrf),
) -> dict[str, str]:
    state = create_oauth_state()
    verifier, challenge = create_pkce_pair()
    db.add(
        OAuthAttempt(
            state=state,
            pkce_verifier=verifier,
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.oauth_state_ttl_seconds),
        )
    )
    db.commit()
    client = YouTubeClient(
        settings.google_client_id,
        settings.google_client_secret.get_secret_value(),
        settings.google_redirect_uri,
    )
    return {"authorization_url": client.authorization_url(state, challenge)}


@router.get("/youtube/callback")
async def youtube_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _=Depends(require_owner),
) -> RedirectResponse:
    attempt = db.get(OAuthAttempt, state)
    now = datetime.now(UTC)
    expires_at = attempt.expires_at if attempt else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if not attempt or attempt.consumed_at or not expires_at or expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    code_verifier = attempt.pkce_verifier
    attempt.consumed_at = now
    attempt.pkce_verifier = ""
    db.commit()

    client = YouTubeClient(
        settings.google_client_id,
        settings.google_client_secret.get_secret_value(),
        settings.google_redirect_uri,
    )
    try:
        tokens = await client.exchange_code(code, code_verifier)
        channel = await client.channel(tokens.access_token)
    except YouTubeProviderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    cipher = TokenCipher(settings.token_encryption_key.get_secret_value())
    connection = db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.provider == "youtube",
            ProviderConnection.external_account_id == channel.channel_id,
        )
    )
    if not connection:
        connection = ProviderConnection(
            external_account_id=channel.channel_id,
            display_name=channel.title,
            encrypted_access_token=cipher.encrypt(tokens.access_token),
        )
        db.add(connection)
    connection.display_name = channel.title
    connection.encrypted_access_token = cipher.encrypt(tokens.access_token)
    if tokens.refresh_token:
        connection.encrypted_refresh_token = cipher.encrypt(tokens.refresh_token)
    connection.scopes = tokens.scopes
    connection.expires_at = tokens.expires_at
    connection.status = "active"
    connection.last_validated_at = now
    db.commit()
    return RedirectResponse(f"{settings.frontend_origin}/?youtube=connected")


@router.get("/youtube/connection")
def youtube_connection(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _=Depends(require_owner),
) -> dict[str, object]:
    connection = db.scalar(
        select(ProviderConnection).where(ProviderConnection.provider == "youtube")
    )
    if not connection:
        return {"connected": False}
    latest_run = db.scalar(
        select(SyncRun)
        .where(SyncRun.connection_id == connection.id)
        .order_by(SyncRun.created_at.desc())
    )
    latest_success = db.scalar(
        select(SyncRun)
        .where(
            SyncRun.connection_id == connection.id,
            SyncRun.status.in_(["succeeded", "partial"]),
        )
        .order_by(SyncRun.finished_at.desc())
    )
    next_due_at = None
    if latest_success and latest_success.finished_at:
        finished_at = utc_value(latest_success.finished_at)
        next_due_at = finished_at + timedelta(hours=settings.youtube_sync_interval_hours)
    return {
        "connected": connection.status == "active",
        "id": connection.id,
        "channel_id": connection.external_account_id,
        "channel_name": connection.display_name,
        "status": connection.status,
        "last_validated_at": utc_value(connection.last_validated_at),
        "latest_run": serialize_run(latest_run) if latest_run else None,
        "schedule": {
            "enabled": settings.scheduled_sync_enabled,
            "interval_hours": settings.youtube_sync_interval_hours,
            "next_due_at": next_due_at,
        },
    }


@router.post("/youtube/sync", status_code=status.HTTP_202_ACCEPTED)
def start_sync(
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _=Depends(require_csrf),
) -> dict[str, object]:
    connection = db.scalar(
        select(ProviderConnection).where(
            ProviderConnection.provider == "youtube", ProviderConnection.status == "active"
        )
    )
    if not connection:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="YouTube is not connected")
    service = YouTubeSyncService(settings, db)
    active = service.active_run(connection.id)
    if active:
        return serialize_run(active)
    run = service.create_run(connection, idempotency_key)
    if run.status == "queued":
        background_tasks.add_task(run_sync_in_new_session, settings, run.id)
    return serialize_run(run)


@router.get("/youtube/sync-runs")
def sync_runs(db: Session = Depends(get_db), _=Depends(require_owner)) -> list[dict[str, object]]:
    connection = db.scalar(
        select(ProviderConnection).where(ProviderConnection.provider == "youtube")
    )
    if not connection:
        return []
    runs = db.scalars(
        select(SyncRun)
        .where(SyncRun.connection_id == connection.id)
        .order_by(SyncRun.created_at.desc())
        .limit(20)
    )
    return [serialize_run(run) for run in runs]


@router.delete("/youtube/connection")
async def disconnect_youtube(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _=Depends(require_csrf),
) -> dict[str, object]:
    connection = db.scalar(
        select(ProviderConnection).where(ProviderConnection.provider == "youtube")
    )
    if not connection:
        return {"disconnected": True, "revoked": False}
    revoked = await YouTubeSyncService(settings, db).disconnect(connection)
    return {"disconnected": True, "revoked": revoked}


@router.get("/workspace/overview")
def workspace_overview(
    db: Session = Depends(get_db), _=Depends(require_owner)
) -> dict[str, object]:
    connection = db.scalar(
        select(ProviderConnection).where(ProviderConnection.provider == "youtube")
    )
    latest_run = None
    if connection:
        latest_run = db.scalar(
            select(SyncRun)
            .where(
                SyncRun.connection_id == connection.id,
                SyncRun.status.in_(["succeeded", "partial"]),
            )
            .order_by(SyncRun.finished_at.desc())
        )
    available_metrics = db.scalar(
        select(func.count(MetricObservation.id)).where(
            MetricObservation.availability == "available",
            MetricObservation.value.is_not(None),
        )
    )
    return {
        "youtube_connected": bool(connection and connection.status == "active"),
        "youtube_channel_name": connection.display_name if connection else None,
        "last_synced_at": utc_value(latest_run.finished_at) if latest_run else None,
        "available_metric_observations": available_metrics or 0,
        "tracked_content_count": db.scalar(select(func.count(ContentItem.id))) or 0,
        "watchlist_count": db.scalar(select(func.count(CreatorWatchlistItem.id))) or 0,
        "content_project_count": db.scalar(select(func.count(ContentProject.id))) or 0,
        "business_context_configured": db.get(BusinessContext, "owner") is not None,
    }


@router.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db), _=Depends(require_owner)) -> dict[str, object]:
    connection = db.scalar(
        select(ProviderConnection).where(ProviderConnection.provider == "youtube")
    )
    observations = db.scalars(
        select(MetricObservation)
        .where(MetricObservation.availability == "available")
        .order_by(MetricObservation.period_end.desc(), MetricObservation.retrieved_at.desc())
    ).all()
    latest_by_key: dict[str, MetricObservation] = {}
    for observation in observations:
        latest_by_key.setdefault(observation.metric_key, observation)
    return {
        "provider": "youtube",
        "connected": bool(connection and connection.status == "active"),
        "channel_name": connection.display_name if connection else None,
        "freshness": max((utc_value(item.retrieved_at) for item in observations), default=None),
        "metrics": [
            {
                "key": key,
                "value": observation.value,
                "unit": observation.unit,
                "period_start": observation.period_start,
                "period_end": observation.period_end,
                "availability": observation.availability,
                "reason": observation.reason,
            }
            for key, observation in latest_by_key.items()
        ],
    }


@router.get("/analytics/dashboard")
def analytics_dashboard(
    period: Literal["7d", "28d", "90d", "custom"] = Query(default="90d", alias="range"),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_owner),
) -> dict[str, object]:
    try:
        actual_start, actual_end = resolve_date_range(period, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return dashboard(db, actual_start, actual_end)


@router.get("/analytics/metric-definitions")
def metric_definitions(_=Depends(require_owner)) -> list[dict[str, str]]:
    return [definition.serialize() for definition in OWNED_ANALYTICS_METRICS]


@router.get("/business-context")
def get_business_context(
    db: Session = Depends(get_db), _=Depends(require_owner)
) -> dict[str, object]:
    context = db.get(BusinessContext, "owner")
    if not context:
        return {
            "configured": False,
            "brand_name": "CloudDataFriend",
            "mission": "",
            "target_audience": "",
            "content_pillars": [],
            "business_goals": [],
            "services": [],
            "resources": [],
            "updated_at": None,
        }
    return {"configured": True, **serialize_business_context(context)}


@router.put("/business-context")
def put_business_context(
    payload: BusinessContextPayload,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> dict[str, object]:
    context = db.get(BusinessContext, "owner") or BusinessContext(id="owner")
    for key, value in payload.model_dump().items():
        setattr(context, key, value)
    context.updated_at = utcnow()
    db.add(context)
    db.commit()
    db.refresh(context)
    return {"configured": True, **serialize_business_context(context)}


@router.get("/creators")
def list_creators(
    db: Session = Depends(get_db), _=Depends(require_owner)
) -> list[dict[str, object]]:
    creators = db.scalars(
        select(CreatorWatchlistItem).order_by(CreatorWatchlistItem.created_at.desc())
    )
    return [serialize_creator(creator) for creator in creators]


@router.post("/creators", status_code=status.HTTP_201_CREATED)
def create_creator(
    payload: CreatorPayload,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> dict[str, object]:
    creator = CreatorWatchlistItem(
        **payload.model_dump(exclude={"profile_url"}),
        profile_url=str(payload.profile_url),
    )
    db.add(creator)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This creator profile is already on the watchlist",
        ) from exc
    db.refresh(creator)
    return serialize_creator(creator)


@router.patch("/creators/{creator_id}")
def update_creator(
    creator_id: str,
    payload: CreatorUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> dict[str, object]:
    creator = db.get(CreatorWatchlistItem, creator_id)
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("profile_url") is not None:
        data["profile_url"] = str(data["profile_url"])
    for key, value in data.items():
        setattr(creator, key, value)
    creator.updated_at = utcnow()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This creator profile is already on the watchlist",
        ) from exc
    db.refresh(creator)
    return serialize_creator(creator)


@router.get("/creators/{creator_id}/evidence")
def list_creator_evidence(
    creator_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_owner),
) -> list[dict[str, object]]:
    if not db.get(CreatorWatchlistItem, creator_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")
    evidence = db.scalars(
        select(CreatorEvidence)
        .where(CreatorEvidence.creator_id == creator_id)
        .order_by(CreatorEvidence.observed_at.desc())
    )
    return [serialize_creator_evidence(item) for item in evidence]


@router.post("/creators/{creator_id}/evidence", status_code=status.HTTP_201_CREATED)
def create_creator_evidence(
    creator_id: str,
    payload: CreatorEvidencePayload,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> dict[str, object]:
    creator = db.get(CreatorWatchlistItem, creator_id)
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")
    evidence = CreatorEvidence(
        creator_id=creator_id,
        **payload.model_dump(exclude={"source_url", "observed_at"}),
        source_url=str(payload.source_url),
        observed_at=payload.observed_at or utcnow(),
    )
    creator.evidence_checked_at = utcnow()
    creator.updated_at = utcnow()
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return serialize_creator_evidence(evidence)


@router.delete("/creators/{creator_id}/evidence/{evidence_id}", status_code=204)
def delete_creator_evidence(
    creator_id: str,
    evidence_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> None:
    evidence = db.scalar(
        select(CreatorEvidence).where(
            CreatorEvidence.id == evidence_id, CreatorEvidence.creator_id == creator_id
        )
    )
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    db.delete(evidence)
    db.commit()


@router.delete("/creators/{creator_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_creator(
    creator_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> None:
    creator = db.get(CreatorWatchlistItem, creator_id)
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")
    db.delete(creator)
    db.commit()


@router.get("/content-projects")
def list_content_projects(
    db: Session = Depends(get_db), _=Depends(require_owner)
) -> list[dict[str, object]]:
    projects = db.scalars(select(ContentProject).order_by(ContentProject.created_at.desc()))
    return [serialize_content_project(project) for project in projects]


@router.post("/content-projects", status_code=status.HTTP_201_CREATED)
def create_content_project(
    payload: ContentProjectCreate,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> dict[str, object]:
    data = payload.model_dump(exclude={"source_url"})
    project = ContentProject(
        **data,
        source_url=str(payload.source_url) if payload.source_url else None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize_content_project(project)


@router.patch("/content-projects/{project_id}")
def update_content_project(
    project_id: str,
    payload: ContentProjectUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> dict[str, object]:
    project = db.get(ContentProject, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found")
    data = payload.model_dump(exclude_unset=True)
    for url_key in ("source_url", "published_url"):
        if url_key in data and data[url_key] is not None:
            data[url_key] = str(data[url_key])
    for key, value in data.items():
        setattr(project, key, value)
    project.updated_at = utcnow()
    db.commit()
    db.refresh(project)
    return serialize_content_project(project)


@router.delete("/content-projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content_project(
    project_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_csrf),
) -> None:
    project = db.get(ContentProject, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found")
    db.delete(project)
    db.commit()


def serialize_business_context(context: BusinessContext) -> dict[str, object]:
    return {
        "brand_name": context.brand_name,
        "mission": context.mission,
        "target_audience": context.target_audience,
        "content_pillars": context.content_pillars,
        "business_goals": context.business_goals,
        "services": context.services,
        "resources": context.resources,
        "updated_at": utc_value(context.updated_at),
    }


def serialize_creator(creator: CreatorWatchlistItem) -> dict[str, object]:
    return {
        "id": creator.id,
        "name": creator.name,
        "platform": creator.platform,
        "profile_url": creator.profile_url,
        "niche": creator.niche,
        "notes": creator.notes,
        "evidence_checked_at": utc_value(creator.evidence_checked_at),
        "evidence_count": len(creator.evidence),
        "created_at": utc_value(creator.created_at),
        "updated_at": utc_value(creator.updated_at),
    }


def serialize_creator_evidence(evidence: CreatorEvidence) -> dict[str, object]:
    return {
        "id": evidence.id,
        "creator_id": evidence.creator_id,
        "evidence_type": evidence.evidence_type,
        "title": evidence.title,
        "observation": evidence.observation,
        "source_url": evidence.source_url,
        "public_metrics": evidence.public_metrics,
        "limitations": evidence.limitations,
        "observed_at": utc_value(evidence.observed_at),
        "created_at": utc_value(evidence.created_at),
    }


def serialize_content_project(project: ContentProject) -> dict[str, object]:
    return {
        "id": project.id,
        "title": project.title,
        "status": project.status,
        "platform": project.platform,
        "content_type": project.content_type,
        "pillar": project.pillar,
        "hook": project.hook,
        "brief": project.brief,
        "source_url": project.source_url,
        "planned_for": project.planned_for,
        "published_url": project.published_url,
        "created_at": utc_value(project.created_at),
        "updated_at": utc_value(project.updated_at),
    }


def serialize_run(run: SyncRun) -> dict[str, object]:
    return {
        "id": run.id,
        "status": run.status,
        "created_at": utc_value(run.created_at),
        "started_at": utc_value(run.started_at),
        "finished_at": utc_value(run.finished_at),
        "records_read": run.records_read,
        "records_written": run.records_written,
        "records_rejected": run.records_rejected,
        "retry_count": run.retry_count,
        "error_code": run.error_code,
        "error_summary": run.error_summary,
    }
