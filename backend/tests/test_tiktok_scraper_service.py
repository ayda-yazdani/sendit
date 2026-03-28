import httpx
import pytest
from fastapi import HTTPException

from app.schemas.tiktok import TikTokVideoScrapeRequest
from app.services.tiktok import TikTokVideoScraperService

TIKTOK_HTML = """
<html>
  <head>
    <meta property="og:url" content="https://www.tiktok.com/@creator/video/9876543210" />
    <meta property="og:title" content="Example TikTok title" />
    <meta property="og:description" content="Example TikTok description" />
    <meta property="og:image" content="https://cdn.example.com/tiktok-thumb.jpg" />
    <meta property="og:video" content="https://cdn.example.com/tiktok-video.mp4" />
    <meta property="og:site_name" content="TikTok" />
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": "Example TikTok title",
        "description": "Example TikTok description",
        "thumbnailUrl": "https://cdn.example.com/tiktok-thumb.jpg",
        "contentUrl": "https://cdn.example.com/tiktok-video.mp4",
        "embedUrl": "https://www.tiktok.com/embed/9876543210",
        "uploadDate": "2026-03-27T11:22:33Z",
        "duration": "PT21S",
        "author": {
          "@type": "Person",
          "name": "Creator Name",
          "alternateName": "@creator",
          "url": "https://www.tiktok.com/@creator"
        }
      }
    </script>
  </head>
  <body></body>
</html>
"""


@pytest.mark.anyio
async def test_scrape_video_extracts_tiktok_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            text=TIKTOK_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TikTokVideoScraperService(http_client=client)
        result = await service.scrape_video(
            TikTokVideoScrapeRequest(
                url="https://www.tiktok.com/@creator/video/9876543210"
            )
        )

    assert len(requests) == 1
    assert requests[0].headers["User-Agent"]
    assert str(result.requested_url) == "https://www.tiktok.com/@creator/video/9876543210"
    assert result.video_id == "9876543210"
    assert result.title == "Example TikTok title"
    assert result.description == "Example TikTok description"
    assert str(result.thumbnail_url) == "https://cdn.example.com/tiktok-thumb.jpg"
    assert str(result.video_url) == "https://cdn.example.com/tiktok-video.mp4"
    assert str(result.embed_url) == "https://www.tiktok.com/embed/9876543210"
    assert result.author is not None
    assert result.author.username == "creator"
    assert result.open_graph["og:site_name"] == "TikTok"


@pytest.mark.anyio
async def test_scrape_video_returns_404_for_missing_tiktok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TikTokVideoScraperService(http_client=client)
        with pytest.raises(HTTPException) as exc_info:
            await service.scrape_video(
                TikTokVideoScrapeRequest(
                    url="https://www.tiktok.com/@creator/video/missing123"
                )
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "TikTok video not found."


@pytest.mark.anyio
async def test_scrape_video_returns_502_when_metadata_cannot_be_extracted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body>No metadata here</body></html>",
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TikTokVideoScraperService(http_client=client)
        with pytest.raises(HTTPException) as exc_info:
            await service.scrape_video(
                TikTokVideoScrapeRequest(
                    url="https://www.tiktok.com/@creator/video/empty123"
                )
            )

    assert exc_info.value.status_code == 502
    assert (
        exc_info.value.detail
        == "Could not extract TikTok video metadata from the response."
    )
