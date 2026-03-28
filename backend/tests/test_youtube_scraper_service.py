import httpx
import pytest
from fastapi import HTTPException

from app.schemas.youtube import YouTubeShortScrapeRequest
from app.services.youtube import YouTubeShortsScraperService

YOUTUBE_HTML = """
<html>
  <head>
    <link rel="canonical" href="https://www.youtube.com/shorts/xyz987" />
    <meta property="og:url" content="https://www.youtube.com/shorts/xyz987" />
    <meta property="og:title" content="Example Short title" />
    <meta property="og:description" content="Example Short description" />
    <meta property="og:image" content="https://cdn.example.com/youtube-thumb.jpg" />
    <meta property="og:site_name" content="YouTube" />
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": "Example Short title",
        "description": "Example Short description",
        "thumbnailUrl": "https://cdn.example.com/youtube-thumb.jpg",
        "embedUrl": "https://www.youtube.com/embed/xyz987",
        "uploadDate": "2026-03-27T11:22:33Z",
        "duration": "PT43S",
        "author": {
          "@type": "Person",
          "name": "Shorts Creator",
          "url": "https://www.youtube.com/@shortscreator",
          "identifier": "UC123456789"
        }
      }
    </script>
  </head>
  <body></body>
</html>
"""

YOUTUBE_SPARSE_HTML = """
<html>
  <head>
    <link rel="canonical" href="https://www.youtube.com/shorts/xyz987" />
    <meta name="twitter:title" content="Sparse Short title" />
    <meta name="description" content="Sparse Short description" />
    <meta name="twitter:image" content="https://cdn.example.com/sparse-thumb.jpg" />
  </head>
  <body></body>
</html>
"""

YOUTUBE_PLAYER_RESPONSE_HTML = """
<html>
  <head>
    <link rel="canonical" href="https://www.youtube.com/shorts/xyz987" />
    <script>
      var ytInitialPlayerResponse = {
        "videoDetails": {
          "title": "Player Response Short",
          "shortDescription": "Extracted from ytInitialPlayerResponse",
          "lengthSeconds": "59",
          "channelId": "UCPLAYER123",
          "author": "Player Creator",
          "thumbnail": {
            "thumbnails": [
              {"url": "https://cdn.example.com/player-thumb-small.jpg"},
              {"url": "https://cdn.example.com/player-thumb-large.jpg"}
            ]
          }
        },
        "microformat": {
          "playerMicroformatRenderer": {
            "ownerProfileUrl": "https://www.youtube.com/@playercreator"
          }
        }
      };
    </script>
  </head>
  <body></body>
</html>
"""

YOUTUBE_CONSENT_HTML = """
<html>
  <head>
    <link rel="canonical" href="https://consent.youtube.com/m" />
  </head>
  <body>Consent required</body>
</html>
"""

YOUTUBE_OEMBED_RESPONSE = """
{
  "title": "Popular Memes (Then Vs Now) #shorts #memes #nostalgia",
  "author_name": "BRANDOMEMES",
  "author_url": "https://www.youtube.com/@BrandoMemes",
  "type": "video",
  "height": 200,
  "width": 113,
  "version": "1.0",
  "provider_name": "YouTube",
  "provider_url": "https://www.youtube.com/",
  "thumbnail_height": 360,
  "thumbnail_width": 480,
  "thumbnail_url": "https://i.ytimg.com/vi/kgU2-KfUIrE/hq2.jpg",
  "html": "<iframe width=\\\"113\\\" height=\\\"200\\\" src=\\\"https://www.youtube.com/embed/kgU2-KfUIrE?feature=oembed\\\"></iframe>"
}
"""


@pytest.mark.anyio
async def test_scrape_short_extracts_youtube_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            text=YOUTUBE_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = YouTubeShortsScraperService(http_client=client)
        result = await service.scrape_short(
            YouTubeShortScrapeRequest(url="https://www.youtube.com/shorts/xyz987")
        )

    assert len(requests) == 1
    assert requests[0].headers["User-Agent"]
    assert str(result.requested_url) == "https://www.youtube.com/shorts/xyz987"
    assert result.short_id == "xyz987"
    assert result.title == "Example Short title"
    assert result.description == "Example Short description"
    assert str(result.thumbnail_url) == "https://cdn.example.com/youtube-thumb.jpg"
    assert str(result.cover_image_url) == "https://cdn.example.com/youtube-thumb.jpg"
    assert str(result.embed_url) == "https://www.youtube.com/embed/xyz987"
    assert result.channel is not None
    assert result.user is not None
    assert result.channel.handle == "shortscreator"
    assert result.channel.channel_id == "UC123456789"
    assert result.open_graph["og:site_name"] == "YouTube"


@pytest.mark.anyio
async def test_scrape_short_falls_back_to_non_og_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=YOUTUBE_SPARSE_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = YouTubeShortsScraperService(http_client=client)
        result = await service.scrape_short(
            YouTubeShortScrapeRequest(url="https://www.youtube.com/shorts/xyz987")
        )

    assert result.short_id == "xyz987"
    assert result.title == "Sparse Short title"
    assert result.description == "Sparse Short description"
    assert str(result.thumbnail_url) == "https://cdn.example.com/sparse-thumb.jpg"
    assert str(result.canonical_url) == "https://www.youtube.com/shorts/xyz987"
    assert str(result.embed_url) == "https://www.youtube.com/embed/xyz987"


@pytest.mark.anyio
async def test_scrape_short_falls_back_to_initial_player_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=YOUTUBE_PLAYER_RESPONSE_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = YouTubeShortsScraperService(http_client=client)
        result = await service.scrape_short(
            YouTubeShortScrapeRequest(url="https://www.youtube.com/shorts/xyz987")
        )

    assert result.short_id == "xyz987"
    assert result.title == "Player Response Short"
    assert result.description == "Extracted from ytInitialPlayerResponse"
    assert result.duration == "PT59S"
    assert str(result.thumbnail_url) == "https://cdn.example.com/player-thumb-large.jpg"
    assert result.channel is not None
    assert result.channel.name == "Player Creator"
    assert result.channel.handle == "playercreator"
    assert result.channel.channel_id == "UCPLAYER123"


@pytest.mark.anyio
async def test_scrape_short_retries_when_youtube_redirects_to_consent() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "consent.youtube.com":
            return httpx.Response(
                200,
                text=YOUTUBE_CONSENT_HTML,
                headers={"Content-Type": "text/html; charset=utf-8"},
                request=request,
            )

        if "CONSENT" in request.headers.get("cookie", ""):
            return httpx.Response(
                200,
                text=YOUTUBE_PLAYER_RESPONSE_HTML,
                headers={"Content-Type": "text/html; charset=utf-8"},
                request=request,
            )

        return httpx.Response(
            302,
            headers={
                "Location": "https://consent.youtube.com/m?continue=https%3A%2F%2Fwww.youtube.com%2Fshorts%2FkgU2-KfUIrE"
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = YouTubeShortsScraperService(http_client=client)
        result = await service.scrape_short(
            YouTubeShortScrapeRequest(url="https://www.youtube.com/shorts/kgU2-KfUIrE")
        )

    assert len(requests) >= 3
    assert result.title == "Player Response Short"
    assert result.short_id == "kgU2-KfUIrE"


@pytest.mark.anyio
async def test_scrape_short_falls_back_to_oembed_when_page_metadata_is_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oembed":
            return httpx.Response(
                200,
                text=YOUTUBE_OEMBED_RESPONSE,
                headers={"Content-Type": "application/json"},
                request=request,
            )
        return httpx.Response(
            200,
            text=YOUTUBE_CONSENT_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = YouTubeShortsScraperService(http_client=client)
        result = await service.scrape_short(
            YouTubeShortScrapeRequest(url="https://www.youtube.com/shorts/kgU2-KfUIrE")
        )

    assert result.short_id == "kgU2-KfUIrE"
    assert result.title == "Popular Memes (Then Vs Now) #shorts #memes #nostalgia"
    assert str(result.thumbnail_url) == "https://i.ytimg.com/vi/kgU2-KfUIrE/hq2.jpg"
    assert str(result.embed_url) == "https://www.youtube.com/embed/kgU2-KfUIrE?feature=oembed"
    assert result.channel is not None
    assert result.channel.name == "BRANDOMEMES"
    assert result.channel.handle == "BrandoMemes"


@pytest.mark.anyio
async def test_scrape_short_returns_404_for_missing_short() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = YouTubeShortsScraperService(http_client=client)
        with pytest.raises(HTTPException) as exc_info:
            await service.scrape_short(
                YouTubeShortScrapeRequest(url="https://www.youtube.com/shorts/missing")
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "YouTube Short not found."


@pytest.mark.anyio
async def test_scrape_short_returns_partial_response_when_only_short_id_is_known() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body>No metadata here</body></html>",
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = YouTubeShortsScraperService(http_client=client)
        result = await service.scrape_short(
            YouTubeShortScrapeRequest(url="https://www.youtube.com/shorts/empty123")
        )

    assert result.short_id == "empty123"
    assert str(result.canonical_url) == "https://www.youtube.com/shorts/empty123"
    assert str(result.embed_url) == "https://www.youtube.com/embed/empty123"
    assert result.title is None
    assert result.description is None
    assert result.thumbnail_url is None
