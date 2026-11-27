from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.entities import (
    CreatorResearchRun,
    CreatorVideo,
    CreatorVideoComment,
    CreatorWatchlistItem,
    ProviderConnection,
)
from app.providers.youtube.client import YouTubeClient, YouTubeProviderError
from app.services.youtube_sync import YouTubeSyncService


class CreatorResearchService:
    VIDEO_LIMIT = 20
    COMMENT_VIDEO_LIMIT = 5
    COMMENT_LIMIT = 100

    def __init__(self, settings: Settings, session: Session) -> None:
        self.settings = settings
        self.session = session
        self.client = YouTubeClient(
            settings.google_client_id,
            settings.google_client_secret.get_secret_value(),
            settings.google_redirect_uri,
            api_key=settings.youtube_api_key.get_secret_value(),
        )

    async def refresh(self, creator: CreatorWatchlistItem) -> CreatorResearchRun:
        profile = next(
            (item for item in creator.profiles if item.platform == "youtube"), None
        )
        if not profile:
            raise YouTubeProviderError(
                "youtube_profile_required", "Add a YouTube profile before refreshing research"
            )
        connection = self.session.scalar(
            select(ProviderConnection).where(
                ProviderConnection.provider == "youtube",
                ProviderConnection.status == "active",
            )
        )
        if not connection:
            raise YouTubeProviderError(
                "authorization_required",
                "Connect CloudDataFriend YouTube before refreshing creator research",
            )

        run = CreatorResearchRun(creator_id=creator.id)
        self.session.add(run)
        self.session.commit()
        try:
            token = await YouTubeSyncService(
                self.settings, self.session
            ).valid_access_token(connection)
            if not profile.provider_account_id or not profile.uploads_playlist_id:
                channel = await self.client.public_channel(token, profile.profile_url)
                profile.provider_account_id = channel.channel_id
                profile.uploads_playlist_id = channel.uploads_playlist_id
                run.estimated_quota_units += 1

            videos = await self.client.public_videos(
                token, profile.uploads_playlist_id, self.VIDEO_LIMIT
            )
            run.estimated_quota_units += 2
            run.records_read += len(videos)
            stored: list[CreatorVideo] = []
            now = datetime.now(UTC)
            for video in videos:
                record = self.session.scalar(
                    select(CreatorVideo).where(
                        CreatorVideo.provider == "youtube",
                        CreatorVideo.provider_video_id == video.video_id,
                    )
                )
                if not record:
                    record = CreatorVideo(
                        creator_id=creator.id,
                        provider_video_id=video.video_id,
                        title=video.title,
                        description=video.description,
                        source_url=f"https://www.youtube.com/watch?v={video.video_id}",
                        thumbnail_url=video.thumbnail_url,
                        published_at=video.published_at,
                        duration_seconds=video.duration_seconds,
                        views=video.views,
                        likes=video.likes,
                        comments_count=video.comments,
                    )
                    self.session.add(record)
                    self.session.flush()
                    run.records_written += 1
                else:
                    record.creator_id = creator.id
                    record.title = video.title
                    record.description = video.description
                    record.thumbnail_url = video.thumbnail_url
                    record.published_at = video.published_at
                    record.duration_seconds = video.duration_seconds
                    record.views = video.views
                    record.likes = video.likes
                    record.comments_count = video.comments
                    record.retrieved_at = now
                stored.append(record)

            comment_failures: Counter[str] = Counter()
            priority = sorted(
                (video for video in stored if video.views is not None),
                key=lambda item: item.views or 0,
                reverse=True,
            )[: self.COMMENT_VIDEO_LIMIT]
            for video in priority:
                run.estimated_quota_units += 1
                try:
                    comments = await self.client.public_comments(
                        token, video.provider_video_id, self.COMMENT_LIMIT
                    )
                except YouTubeProviderError as exc:
                    comment_failures[exc.code] += 1
                    continue
                run.records_read += len(comments)
                for comment in comments:
                    existing = self.session.scalar(
                        select(CreatorVideoComment).where(
                            CreatorVideoComment.provider == "youtube",
                            CreatorVideoComment.provider_comment_id == comment.comment_id,
                        )
                    )
                    if not existing:
                        self.session.add(
                            CreatorVideoComment(
                                video_id=video.id,
                                provider_comment_id=comment.comment_id,
                                text=comment.text,
                                author_name=comment.author_name,
                                like_count=comment.like_count,
                                published_at=comment.published_at,
                                source_url=(
                                    f"https://www.youtube.com/watch?v={video.provider_video_id}"
                                    f"&lc={comment.comment_id}"
                                ),
                            )
                        )
                        run.records_written += 1
                    else:
                        existing.text = comment.text
                        existing.author_name = comment.author_name
                        existing.like_count = comment.like_count
                        existing.retrieved_at = now

            profile.last_synced_at = now
            creator.evidence_checked_at = now
            creator.updated_at = now
            run.status = "partial" if comment_failures else "succeeded"
            if comment_failures:
                count = sum(comment_failures.values())
                if set(comment_failures) == {"comments_disabled"}:
                    run.error_summary = f"Comments are disabled for {count} priority video(s)"
                elif "quota_exceeded" in comment_failures:
                    run.error_summary = (
                        "YouTube comment collection reached the project's daily API quota"
                    )
                elif "insufficient_permissions" in comment_failures:
                    run.error_summary = (
                        "YouTube denied OAuth comment access. Configure a restricted "
                        "YOUTUBE_API_KEY for public comment research."
                    )
                elif "public_api_key_required" in comment_failures:
                    run.error_summary = (
                        "Configure a restricted YOUTUBE_API_KEY to collect public comments "
                        "and audience questions."
                    )
                else:
                    reasons = ", ".join(
                        f"{code}: {failures}"
                        for code, failures in sorted(comment_failures.items())
                    )
                    run.error_summary = (
                        f"Comments were unavailable for {count} priority video(s) ({reasons})"
                    )
            run.finished_at = now
            self.session.commit()
            self.session.refresh(run)
            return run
        except Exception as exc:
            self.session.rollback()
            failed = self.session.get(CreatorResearchRun, run.id)
            if failed:
                failed.status = "failed"
                failed.error_summary = str(exc)[:500]
                failed.finished_at = datetime.now(UTC)
                self.session.commit()
            raise
