import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
YOUTUBE_SCOPES = (YOUTUBE_READONLY_SCOPE, YOUTUBE_ANALYTICS_SCOPE)


class YouTubeProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: list[str]


@dataclass(frozen=True)
class YouTubeChannel:
    channel_id: str
    title: str
    uploads_playlist_id: str


@dataclass(frozen=True)
class YouTubeVideo:
    video_id: str
    title: str
    published_at: datetime
    duration_seconds: int | None


@dataclass(frozen=True)
class MetricValue:
    video_id: str
    day: date
    metric_key: str
    unit: str
    value: float


@dataclass(frozen=True)
class YouTubePublicVideo:
    video_id: str
    title: str
    description: str
    published_at: datetime
    duration_seconds: int | None
    thumbnail_url: str | None
    views: int | None
    likes: int | None
    comments: int | None


@dataclass(frozen=True)
class YouTubePublicComment:
    comment_id: str
    text: str
    author_name: str | None
    like_count: int | None
    published_at: datetime


def parse_iso8601_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
        value,
    )
    if not match:
        return None
    parts = {name: int(number or 0) for name, number in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


class YouTubeClient:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    DATA_API = "https://www.googleapis.com/youtube/v3"
    ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        *,
        api_key: str = "",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _google_error_reason(response: httpx.Response) -> str | None:
        """Read Google's stable error reason without retaining response content."""
        try:
            errors = response.json().get("error", {}).get("errors", [])
        except (ValueError, AttributeError):
            return None
        if not errors or not isinstance(errors[0], dict):
            return None
        reason = errors[0].get("reason")
        return str(reason) if reason else None

    def authorization_url(self, state: str, code_challenge: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def _request(
        self,
        method: str,
        url: str,
        *,
        attempts: int = 3,
        **kwargs: Any,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for attempt in range(attempts):
                try:
                    response = await client.request(method, url, **kwargs)
                except httpx.TransportError as exc:
                    if attempt + 1 == attempts:
                        raise YouTubeProviderError(
                            "transport_error", "YouTube is unavailable", retryable=True
                        ) from exc
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt + 1 == attempts:
                        raise YouTubeProviderError(
                            "rate_limited"
                            if response.status_code == 429
                            else "provider_unavailable",
                            "YouTube request could not be completed",
                            retryable=True,
                        )
                    retry_after = response.headers.get("retry-after")
                    delay = (
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else 0.25 * (2**attempt)
                    )
                    await asyncio.sleep(min(delay, 5.0))
                    continue
                reason = self._google_error_reason(response)
                if response.status_code == 400:
                    if reason == "commentsDisabled":
                        raise YouTubeProviderError(
                            "comments_disabled", "Comments are disabled for this video"
                        )
                    raise YouTubeProviderError(
                        "invalid_request", "YouTube rejected this request"
                    )
                if response.status_code == 401:
                    raise YouTubeProviderError(
                        "authorization_required", "YouTube authorization is invalid"
                    )
                if response.status_code == 403:
                    if reason == "commentsDisabled":
                        raise YouTubeProviderError(
                            "comments_disabled", "Comments are disabled for this video"
                        )
                    if reason in {"quotaExceeded", "dailyLimitExceeded"}:
                        raise YouTubeProviderError(
                            "quota_exceeded", "The YouTube API quota has been exhausted"
                        )
                    if reason in {"insufficientPermissions", "forbidden"}:
                        raise YouTubeProviderError(
                            "insufficient_permissions",
                            "YouTube did not grant access to this resource",
                        )
                    raise YouTubeProviderError(
                        "access_forbidden",
                        "YouTube denied this request; check API access, scopes and quota",
                    )
                if response.status_code == 404:
                    raise YouTubeProviderError(
                        "provider_not_found", "The requested YouTube resource was not found"
                    )
                if response.is_error:
                    raise YouTubeProviderError("provider_rejected", "YouTube rejected the request")
                return response
        raise AssertionError("unreachable")

    async def exchange_code(self, code: str, code_verifier: str) -> OAuthTokens:
        response = await self._request(
            "POST",
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            },
        )
        payload = response.json()
        expires_in = payload.get("expires_in")
        return OAuthTokens(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=(
                datetime.now(UTC) + timedelta(seconds=int(expires_in)) if expires_in else None
            ),
            scopes=str(payload.get("scope", "")).split(),
        )

    async def refresh(self, refresh_token: str) -> OAuthTokens:
        response = await self._request(
            "POST",
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        payload = response.json()
        expires_in = payload.get("expires_in")
        return OAuthTokens(
            access_token=payload["access_token"],
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=int(expires_in or 3600)),
            scopes=str(payload.get("scope", "")).split(),
        )

    async def channel(self, access_token: str) -> YouTubeChannel:
        response = await self._request(
            "GET",
            f"{self.DATA_API}/channels",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"part": "snippet,contentDetails", "mine": "true"},
        )
        items = response.json().get("items", [])
        if len(items) != 1:
            raise YouTubeProviderError("channel_not_found", "No eligible YouTube channel was found")
        item = items[0]
        return YouTubeChannel(
            channel_id=item["id"],
            title=item["snippet"]["title"],
            uploads_playlist_id=item["contentDetails"]["relatedPlaylists"]["uploads"],
        )

    async def public_channel(self, access_token: str, profile_url: str) -> YouTubeChannel:
        path = urlparse(profile_url).path.strip("/")
        params: dict[str, str] = {"part": "snippet,contentDetails"}
        if path.startswith("@"):
            params["forHandle"] = path
        elif path.startswith("channel/") and len(path.split("/", 1)[1]) > 0:
            params["id"] = path.split("/", 1)[1]
        elif path and "/" not in path:
            params["forUsername"] = path
        else:
            raise YouTubeProviderError(
                "unsupported_channel_url",
                "Use a YouTube username, @handle or /channel/ URL",
            )
        response = await self._request(
            "GET",
            f"{self.DATA_API}/channels",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        items = response.json().get("items", [])
        if len(items) != 1:
            raise YouTubeProviderError(
                "channel_not_found", "The saved YouTube channel was not found"
            )
        item = items[0]
        return YouTubeChannel(
            channel_id=item["id"],
            title=item["snippet"]["title"],
            uploads_playlist_id=item["contentDetails"]["relatedPlaylists"]["uploads"],
        )

    async def public_videos(
        self, access_token: str, uploads_playlist_id: str, limit: int = 20
    ) -> list[YouTubePublicVideo]:
        playlist = await self._request(
            "GET",
            f"{self.DATA_API}/playlistItems",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "part": "contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": min(limit, 50),
            },
        )
        video_ids = [
            item["contentDetails"]["videoId"]
            for item in playlist.json().get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        ]
        if not video_ids:
            return []
        response = await self._request(
            "GET",
            f"{self.DATA_API}/videos",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
                "maxResults": 50,
            },
        )
        results: list[YouTubePublicVideo] = []
        for item in response.json().get("items", []):
            snippet = item["snippet"]
            statistics = item.get("statistics", {})
            thumbnails = snippet.get("thumbnails", {})
            thumbnail = (
                thumbnails.get("high")
                or thumbnails.get("medium")
                or thumbnails.get("default")
            )
            results.append(
                YouTubePublicVideo(
                    video_id=item["id"],
                    title=snippet["title"],
                    description=snippet.get("description", ""),
                    published_at=datetime.fromisoformat(
                        snippet["publishedAt"].replace("Z", "+00:00")
                    ),
                    duration_seconds=parse_iso8601_duration(
                        item.get("contentDetails", {}).get("duration")
                    ),
                    thumbnail_url=thumbnail.get("url") if thumbnail else None,
                    views=int(statistics["viewCount"]) if "viewCount" in statistics else None,
                    likes=int(statistics["likeCount"]) if "likeCount" in statistics else None,
                    comments=(
                        int(statistics["commentCount"])
                        if "commentCount" in statistics
                        else None
                    ),
                )
            )
        return results

    async def public_comments(
        self, _access_token: str, video_id: str, limit: int = 100
    ) -> list[YouTubePublicComment]:
        if not self.api_key:
            raise YouTubeProviderError(
                "public_api_key_required",
                "A restricted YouTube API key is required for public comment research",
            )
        response = await self._request(
            "GET",
            f"{self.DATA_API}/commentThreads",
            params={
                "part": "snippet",
                "videoId": video_id,
                "order": "relevance",
                "textFormat": "plainText",
                "maxResults": min(limit, 100),
                "key": self.api_key,
            },
            attempts=1,
        )
        comments: list[YouTubePublicComment] = []
        for item in response.json().get("items", []):
            top = item.get("snippet", {}).get("topLevelComment", {})
            snippet = top.get("snippet", {})
            published_at = snippet.get("publishedAt")
            if not top.get("id") or not published_at:
                continue
            comments.append(
                YouTubePublicComment(
                    comment_id=top["id"],
                    text=snippet.get("textDisplay", ""),
                    author_name=snippet.get("authorDisplayName"),
                    like_count=(
                        int(snippet["likeCount"])
                        if snippet.get("likeCount") is not None
                        else None
                    ),
                    published_at=datetime.fromisoformat(published_at.replace("Z", "+00:00")),
                )
            )
        return comments

    async def videos(
        self, access_token: str, uploads_playlist_id: str, limit: int
    ) -> list[YouTubeVideo]:
        video_ids: list[str] = []
        page_token: str | None = None
        while len(video_ids) < limit:
            params = {
                "part": "contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": min(50, limit - len(video_ids)),
            }
            if page_token:
                params["pageToken"] = page_token
            response = await self._request(
                "GET",
                f"{self.DATA_API}/playlistItems",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            payload = response.json()
            video_ids.extend(
                item["contentDetails"]["videoId"]
                for item in payload.get("items", [])
                if item.get("contentDetails", {}).get("videoId")
            )
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        videos: list[YouTubeVideo] = []
        for offset in range(0, len(video_ids), 50):
            response = await self._request(
                "GET",
                f"{self.DATA_API}/videos",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "part": "snippet,contentDetails",
                    "id": ",".join(video_ids[offset : offset + 50]),
                    "maxResults": 50,
                },
            )
            for item in response.json().get("items", []):
                published = datetime.fromisoformat(
                    item["snippet"]["publishedAt"].replace("Z", "+00:00")
                )
                videos.append(
                    YouTubeVideo(
                        video_id=item["id"],
                        title=item["snippet"]["title"],
                        published_at=published,
                        duration_seconds=parse_iso8601_duration(
                            item["contentDetails"].get("duration")
                        ),
                    )
                )
        return videos

    async def analytics(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        video_ids: list[str],
    ) -> list[MetricValue]:
        metric_units = {
            "views": "count",
            "estimatedMinutesWatched": "minutes",
            "averageViewDuration": "seconds",
            "likes": "count",
            "comments": "count",
            "subscribersGained": "count",
            "subscribersLost": "count",
        }
        results: list[MetricValue] = []
        if not video_ids:
            return results

        page_size = 200
        # YouTube only permits the video dimension when the request also
        # filters to one or more video IDs. A filter accepts at most 500 IDs.
        for offset in range(0, len(video_ids), 500):
            video_batch = video_ids[offset : offset + 500]
            start_index = 1
            while True:
                response = await self._request(
                    "GET",
                    f"{self.ANALYTICS_API}/reports",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={
                        "ids": "channel==MINE",
                        "startDate": start_date.isoformat(),
                        "endDate": end_date.isoformat(),
                        "dimensions": "day,video",
                        "filters": f"video=={','.join(video_batch)}",
                        "metrics": ",".join(metric_units),
                        "sort": "day",
                        "maxResults": page_size,
                        "startIndex": start_index,
                    },
                )
                payload = response.json()
                headers = [header["name"] for header in payload.get("columnHeaders", [])]
                rows = payload.get("rows", []) or []
                for raw_row in rows:
                    row = dict(zip(headers, raw_row, strict=True))
                    for key, unit in metric_units.items():
                        if row.get(key) is not None:
                            results.append(
                                MetricValue(
                                    video_id=str(row["video"]),
                                    day=date.fromisoformat(str(row["day"])),
                                    metric_key=key,
                                    unit=unit,
                                    value=float(row[key]),
                                )
                            )
                if len(rows) < page_size:
                    break
                start_index += page_size
        return results

    async def revoke(self, token: str) -> bool:
        try:
            response = await self._request(
                "POST", self.REVOKE_URL, params={"token": token}, attempts=1
            )
        except YouTubeProviderError:
            return False
        return response.status_code == 200
