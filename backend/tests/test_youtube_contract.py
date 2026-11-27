from datetime import date

import httpx
import pytest

from app.providers.youtube.client import (
    YouTubeClient,
    YouTubeProviderError,
    parse_iso8601_duration,
)


def test_iso_duration_parser() -> None:
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration("PT45S") == 45
    assert parse_iso8601_duration(None) is None
    assert parse_iso8601_duration("invalid") is None


def test_authorization_url_is_read_only_and_uses_pkce() -> None:
    client = YouTubeClient("client", "secret", "https://example.test/callback")
    url = client.authorization_url("state-value", "challenge-value")

    assert "youtube.readonly" in url
    assert "yt-analytics.readonly" in url
    assert "code_challenge=challenge-value" in url
    assert "youtube.upload" not in url
    assert "youtube.force-ssl" not in url


@pytest.mark.asyncio
async def test_public_channel_resolves_a_legacy_username_without_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = YouTubeClient("client", "secret", "https://example.test/callback")
    response = httpx.Response(
        200,
        json={
            "items": [
                {
                    "id": "channel-keerti",
                    "snippet": {"title": "Keerti Purswani"},
                    "contentDetails": {
                        "relatedPlaylists": {"uploads": "uploads-keerti"}
                    },
                }
            ]
        },
    )
    request_params = {}

    async def fake_request(*args, **kwargs):
        request_params.update(kwargs["params"])
        return response

    monkeypatch.setattr(client, "_request", fake_request)
    channel = await client.public_channel(
        "token", "https://www.youtube.com/keertipurswani"
    )

    assert channel.channel_id == "channel-keerti"
    assert request_params["forUsername"] == "keertipurswani"
    assert "forHandle" not in request_params


@pytest.mark.asyncio
async def test_public_comments_use_api_key_instead_of_owner_oauth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = YouTubeClient(
        "client", "secret", "https://example.test/callback", api_key="public-key"
    )
    response = httpx.Response(200, json={"items": []})
    request_kwargs = {}

    async def fake_request(*args, **kwargs):
        request_kwargs.update(kwargs)
        return response

    monkeypatch.setattr(client, "_request", fake_request)
    comments = await client.public_comments("owner-token", "video-1")

    assert comments == []
    assert request_kwargs["params"]["key"] == "public-key"
    assert "headers" not in request_kwargs


@pytest.mark.asyncio
async def test_public_comments_require_a_public_api_key() -> None:
    client = YouTubeClient("client", "secret", "https://example.test/callback")

    with pytest.raises(YouTubeProviderError) as error:
        await client.public_comments("owner-token", "video-1")

    assert error.value.code == "public_api_key_required"


@pytest.mark.asyncio
async def test_analytics_contract_maps_zero_as_a_real_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = YouTubeClient("client", "secret", "https://example.test/callback")
    payload = {
        "columnHeaders": [
            {"name": "day"},
            {"name": "video"},
            {"name": "views"},
            {"name": "estimatedMinutesWatched"},
            {"name": "averageViewDuration"},
            {"name": "likes"},
            {"name": "comments"},
            {"name": "subscribersGained"},
            {"name": "subscribersLost"},
        ],
        "rows": [["2026-11-24", "video-1", 0, 0, 0, 0, 0, 0, 0]],
    }
    response = httpx.Response(200, json=payload)
    request_params = {}

    async def fake_request(*args, **kwargs):
        request_params.update(kwargs["params"])
        return response

    monkeypatch.setattr(client, "_request", fake_request)
    metrics = await client.analytics("token", date(2026, 11, 24), date(2026, 11, 24), ["video-1"])

    views = next(metric for metric in metrics if metric.metric_key == "views")
    assert views.value == 0
    assert views.video_id == "video-1"
    assert request_params["dimensions"] == "day,video"
    assert request_params["filters"] == "video==video-1"
