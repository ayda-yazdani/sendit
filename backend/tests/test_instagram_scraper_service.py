import httpx
import pytest
from fastapi import HTTPException

from app.schemas.instagram import InstagramReelScrapeRequest
from app.schemas.media import MediaFrame
from app.services.instagram import InstagramReelScraperService

EXPECTED_FRAMES = [
    MediaFrame(
        image_url=f"data:image/jpeg;base64,instagram-{index}",
        timestamp_seconds=float(index * 2),
        timestamp_text=f"0:{index * 2:02d}",
    )
    for index in range(8)
]


class StubFrameService:
    async def extract_frame_captures(self, **_: object) -> list[MediaFrame]:
        return EXPECTED_FRAMES


INSTAGRAM_HTML = """
<html>
  <head>
    <meta property="og:url" content="https://www.instagram.com/reel/abc123/" />
    <meta property="og:title" content="Example reel title" />
    <meta property="og:description" content="Example reel description" />
    <meta property="og:image" content="https://cdn.example.com/thumb.jpg" />
    <meta property="og:video" content="https://cdn.example.com/video.mp4" />
    <meta property="og:site_name" content="Instagram" />
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": "Example reel title",
        "description": "Example reel description",
        "thumbnailUrl": "https://cdn.example.com/thumb.jpg",
        "contentUrl": "https://cdn.example.com/video.mp4",
        "embedUrl": "https://www.instagram.com/reel/abc123/embed",
        "uploadDate": "2026-03-27T11:22:33Z",
        "duration": "PT15S",
        "author": {
          "@type": "Person",
          "name": "Example Creator",
          "url": "https://www.instagram.com/example_creator/"
        }
      }
    </script>
  </head>
  <body></body>
</html>
"""

INSTAGRAM_SPARSE_HTML = """
<html>
  <head>
    <link rel="canonical" href="https://www.instagram.com/reel/abc123/" />
    <meta name="twitter:title" content="Sparse reel title" />
    <meta name="description" content="Sparse reel description" />
    <meta name="twitter:image" content="https://cdn.example.com/sparse-instagram-thumb.jpg" />
  </head>
  <body></body>
</html>
"""


@pytest.mark.anyio
async def test_scrape_reel_extracts_open_graph_and_json_ld_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            text=INSTAGRAM_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = InstagramReelScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
        result = await service.scrape_reel(
            InstagramReelScrapeRequest(
                url="https://www.instagram.com/reel/abc123/"
            )
        )

    assert len(requests) == 1
    assert requests[0].headers["User-Agent"]
    assert str(requests[0].url) == "https://www.instagram.com/reel/abc123/"
    assert result.reel_id == "abc123"
    assert result.title == "Example reel title"
    assert result.description == "Example reel description"
    assert str(result.thumbnail_url) == "https://cdn.example.com/thumb.jpg"
    assert str(result.cover_image_url) == "https://cdn.example.com/thumb.jpg"
    assert result.frames == EXPECTED_FRAMES
    assert str(result.video_url) == "https://cdn.example.com/video.mp4"
    assert str(result.embed_url) == "https://www.instagram.com/reel/abc123/embed"
    assert result.author is not None
    assert result.user is not None
    assert result.author.username == "example_creator"
    assert result.open_graph["og:site_name"] == "Instagram"
    assert result.json_ld[0]["@type"] == "VideoObject"


@pytest.mark.anyio
async def test_scrape_reel_falls_back_to_non_og_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=INSTAGRAM_SPARSE_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = InstagramReelScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
        result = await service.scrape_reel(
            InstagramReelScrapeRequest(url="https://www.instagram.com/reel/abc123/")
        )

    assert result.reel_id == "abc123"
    assert result.title == "Sparse reel title"
    assert result.description == "Sparse reel description"
    assert (
        str(result.thumbnail_url)
        == "https://cdn.example.com/sparse-instagram-thumb.jpg"
    )
    assert result.frames == EXPECTED_FRAMES
    assert str(result.canonical_url) == "https://www.instagram.com/reel/abc123/"


@pytest.mark.anyio
async def test_scrape_reel_returns_404_for_missing_reel() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = InstagramReelScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.scrape_reel(
                InstagramReelScrapeRequest(
                    url="https://www.instagram.com/reel/missing123/"
                )
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Instagram reel not found."


@pytest.mark.anyio
async def test_scrape_reel_returns_partial_response_when_only_reel_id_is_known() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body>No metadata here</body></html>",
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = InstagramReelScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
        result = await service.scrape_reel(
            InstagramReelScrapeRequest(url="https://www.instagram.com/reel/empty123/")
        )

    assert result.reel_id == "empty123"
    assert str(result.canonical_url) == "https://www.instagram.com/reel/empty123/"
    assert result.title is None
    assert result.description is None
    assert result.thumbnail_url is None
    assert result.frames == EXPECTED_FRAMES
