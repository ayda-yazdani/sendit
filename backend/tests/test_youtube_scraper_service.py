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
async def test_scrape_short_returns_502_when_metadata_cannot_be_extracted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body>No metadata here</body></html>",
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = YouTubeShortsScraperService(http_client=client)
        with pytest.raises(HTTPException) as exc_info:
            await service.scrape_short(
                YouTubeShortScrapeRequest(url="https://www.youtube.com/shorts/empty123")
            )

    assert exc_info.value.status_code == 502
    assert (
        exc_info.value.detail
        == "Could not extract YouTube Short metadata from the response."
    )
