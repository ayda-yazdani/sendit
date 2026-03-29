import httpx
import pytest
from fastapi import HTTPException

from app.schemas.tiktok import TikTokVideoScrapeRequest
from app.schemas.media import MediaFrame
from app.services.tiktok import TikTokVideoScraperService

EXPECTED_FRAMES = [
    MediaFrame(
        image_url=f"data:image/jpeg;base64,tiktok-{index}",
        timestamp_seconds=float(index * 2),
        timestamp_text=f"0:{index * 2:02d}",
    )
    for index in range(8)
]


class StubFrameService:
    async def extract_frame_captures(self, **_: object) -> list[MediaFrame]:
        return EXPECTED_FRAMES


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

TIKTOK_UNIVERSAL_DATA_HTML = """
<html>
  <head>
    <title>TikTok - Make Your Day</title>
    <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">
      {
        "__DEFAULT_SCOPE__": {
          "webapp.video-detail": {
            "statusCode": 0,
            "statusMsg": "",
            "shareMeta": {
              "title": "Creator on TikTok",
              "desc": "Creator's short video with original sound"
            },
            "itemInfo": {
              "itemStruct": {
                "id": "9876543210",
                "desc": "",
                "createTime": "1768157731",
                "video": {
                  "duration": 10,
                  "cover": "https://cdn.example.com/tiktok-thumb.jpg",
                  "playAddr": "https://cdn.example.com/tiktok-video.mp4"
                },
                "author": {
                  "uniqueId": "creator",
                  "nickname": "Creator Name"
                }
              }
            }
          }
        }
      }
    </script>
  </head>
  <body></body>
</html>
"""

TIKTOK_SPARSE_META_HTML = """
<html>
  <head>
    <meta name="twitter:title" content="Creator on TikTok" />
    <meta name="twitter:description" content="A sparse TikTok page" />
    <meta name="twitter:image" content="https://cdn.example.com/tiktok-thumb.jpg" />
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
        service = TikTokVideoScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
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
    assert str(result.cover_image_url) == "https://cdn.example.com/tiktok-thumb.jpg"
    assert result.frames == EXPECTED_FRAMES
    assert str(result.video_url) == "https://cdn.example.com/tiktok-video.mp4"
    assert str(result.embed_url) == "https://www.tiktok.com/embed/9876543210"
    assert result.author is not None
    assert result.user is not None
    assert result.author.username == "creator"
    assert result.open_graph["og:site_name"] == "TikTok"


@pytest.mark.anyio
async def test_scrape_video_falls_back_to_universal_data_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=TIKTOK_UNIVERSAL_DATA_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TikTokVideoScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
        result = await service.scrape_video(
            TikTokVideoScrapeRequest(
                url="https://www.tiktok.com/@creator/video/9876543210"
            )
        )

    assert result.video_id == "9876543210"
    assert result.title == "Creator on TikTok"
    assert result.description == "Creator's short video with original sound"
    assert str(result.thumbnail_url) == "https://cdn.example.com/tiktok-thumb.jpg"
    assert str(result.cover_image_url) == "https://cdn.example.com/tiktok-thumb.jpg"
    assert result.frames == EXPECTED_FRAMES
    assert str(result.video_url) == "https://cdn.example.com/tiktok-video.mp4"
    assert str(result.embed_url) == "https://www.tiktok.com/embed/9876543210"
    assert result.author is not None
    assert result.user is not None
    assert result.author.username == "creator"


@pytest.mark.anyio
async def test_scrape_video_returns_404_for_missing_tiktok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TikTokVideoScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.scrape_video(
                TikTokVideoScrapeRequest(
                    url="https://www.tiktok.com/@creator/video/missing123"
                )
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "TikTok video not found."


@pytest.mark.anyio
async def test_scrape_video_returns_partial_response_when_metadata_cannot_be_extracted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body>No metadata here</body></html>",
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TikTokVideoScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
        result = await service.scrape_video(
            TikTokVideoScrapeRequest(
                url="https://www.tiktok.com/@creator/video/empty123"
            )
        )

    assert result.video_id == "empty123"
    assert str(result.canonical_url) == "https://www.tiktok.com/video/empty123"
    assert str(result.embed_url) == "https://www.tiktok.com/embed/empty123"
    assert result.title is None
    assert result.description is None
    assert result.thumbnail_url is None
    assert result.frames == EXPECTED_FRAMES
    assert result.video_url is None


@pytest.mark.anyio
async def test_scrape_video_falls_back_to_sparse_meta_tags() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=TIKTOK_SPARSE_META_HTML,
            headers={"Content-Type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = TikTokVideoScraperService(
            http_client=client,
            frame_service=StubFrameService(),
        )
        result = await service.scrape_video(
            TikTokVideoScrapeRequest(
                url="https://www.tiktok.com/@creator/video/9876543210"
            )
        )

    assert result.video_id == "9876543210"
    assert result.title == "Creator on TikTok"
    assert result.description == "A sparse TikTok page"
    assert str(result.thumbnail_url) == "https://cdn.example.com/tiktok-thumb.jpg"
    assert result.frames == EXPECTED_FRAMES
    assert str(result.canonical_url) == "https://www.tiktok.com/video/9876543210"
    assert str(result.embed_url) == "https://www.tiktok.com/embed/9876543210"
