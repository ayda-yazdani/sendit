import httpx
import pytest

from app.schemas.instagram import InstagramReelScrapeRequest
from app.services.instagram import InstagramReelScraperService

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
        service = InstagramReelScraperService(http_client=client)
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
    assert str(result.video_url) == "https://cdn.example.com/video.mp4"
    assert str(result.embed_url) == "https://www.instagram.com/reel/abc123/embed"
    assert result.author is not None
    assert result.author.username == "example_creator"
    assert result.open_graph["og:site_name"] == "Instagram"
    assert result.json_ld[0]["@type"] == "VideoObject"
