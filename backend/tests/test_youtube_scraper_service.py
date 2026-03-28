import httpx
import pytest

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
    assert str(result.embed_url) == "https://www.youtube.com/embed/xyz987"
    assert result.channel is not None
    assert result.channel.handle == "shortscreator"
    assert result.channel.channel_id == "UC123456789"
    assert result.open_graph["og:site_name"] == "YouTube"
