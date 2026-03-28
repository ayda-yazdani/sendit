import pytest
from fastapi import HTTPException

from app.schemas.instagram import InstagramReelScrapeResponse
from app.schemas.media import MediaScrapeRequest
from app.schemas.tiktok import TikTokVideoScrapeResponse
from app.schemas.youtube import YouTubeShortScrapeResponse
from app.services.media import MediaScraperService


class StubInstagramService:
    def __init__(self) -> None:
        self.last_url = None

    async def scrape_reel(self, payload) -> InstagramReelScrapeResponse:
        self.last_url = str(payload.url)
        return InstagramReelScrapeResponse(
            requested_url=payload.url,
            resolved_url="https://www.instagram.com/reel/abc123/",
            canonical_url="https://www.instagram.com/reel/abc123/",
            reel_id="abc123",
            title="Example reel",
            description="Example description",
            thumbnail_url="https://cdn.example.com/thumb.jpg",
            video_url="https://cdn.example.com/instagram-video.mp4",
        )


class StubTikTokService:
    def __init__(self) -> None:
        self.last_url = None

    async def scrape_video(self, payload) -> TikTokVideoScrapeResponse:
        self.last_url = str(payload.url)
        return TikTokVideoScrapeResponse(
            requested_url=payload.url,
            resolved_url="https://www.tiktok.com/@creator/video/9876543210",
            canonical_url="https://www.tiktok.com/@creator/video/9876543210",
            video_id="9876543210",
            title="Example TikTok",
            description="Example TikTok description",
            thumbnail_url="https://cdn.example.com/tiktok-thumb.jpg",
            video_url="https://cdn.example.com/tiktok-video.mp4",
        )


class StubYouTubeService:
    def __init__(self) -> None:
        self.last_url = None

    async def scrape_short(self, payload) -> YouTubeShortScrapeResponse:
        self.last_url = str(payload.url)
        return YouTubeShortScrapeResponse(
            requested_url=payload.url,
            resolved_url="https://www.youtube.com/shorts/xyz987",
            canonical_url="https://www.youtube.com/shorts/xyz987",
            short_id="xyz987",
            title="Example Short",
            description="Example Short description",
            thumbnail_url="https://cdn.example.com/youtube-thumb.jpg",
            video_url="https://cdn.example.com/youtube-video.mp4",
        )


def build_service() -> tuple[MediaScraperService, StubInstagramService, StubTikTokService, StubYouTubeService]:
    instagram = StubInstagramService()
    tiktok = StubTikTokService()
    youtube = StubYouTubeService()
    service = MediaScraperService(
        instagram_service=instagram,
        tiktok_service=tiktok,
        youtube_service=youtube,
    )
    return service, instagram, tiktok, youtube


@pytest.mark.parametrize(
    ("url", "expected_platform"),
    [
        ("https://www.instagram.com/reel/abc123/", "instagram"),
        ("https://www.tiktok.com/@creator/video/9876543210", "tiktok"),
        ("https://vm.tiktok.com/ZM123456/", "tiktok"),
        ("https://www.youtube.com/shorts/xyz987", "youtube"),
        ("https://example.com/video/123", None),
    ],
)
def test_detect_platform(url: str, expected_platform: str | None) -> None:
    service, _, _, _ = build_service()

    assert service.detect_platform(url) == expected_platform


@pytest.mark.anyio
async def test_scrape_routes_to_instagram_service_and_normalizes_response() -> None:
    service, instagram, _, _ = build_service()

    result = await service.scrape(
        MediaScrapeRequest(url="https://www.instagram.com/reel/abc123/")
    )

    assert instagram.last_url == "https://www.instagram.com/reel/abc123/"
    assert result.platform == "instagram"
    assert result.media_id == "abc123"
    assert str(result.cover_image_url) == "https://cdn.example.com/thumb.jpg"
    assert str(result.video_url) == "https://cdn.example.com/instagram-video.mp4"


@pytest.mark.anyio
async def test_scrape_routes_to_tiktok_service_and_normalizes_response() -> None:
    service, _, tiktok, _ = build_service()

    result = await service.scrape(
        MediaScrapeRequest(url="https://www.tiktok.com/@creator/video/9876543210")
    )

    assert tiktok.last_url == "https://www.tiktok.com/@creator/video/9876543210"
    assert result.platform == "tiktok"
    assert result.media_id == "9876543210"
    assert str(result.cover_image_url) == "https://cdn.example.com/tiktok-thumb.jpg"
    assert str(result.video_url) == "https://cdn.example.com/tiktok-video.mp4"


@pytest.mark.anyio
async def test_scrape_routes_to_youtube_service_and_normalizes_response() -> None:
    service, _, _, youtube = build_service()

    result = await service.scrape(
        MediaScrapeRequest(url="https://www.youtube.com/shorts/xyz987")
    )

    assert youtube.last_url == "https://www.youtube.com/shorts/xyz987"
    assert result.platform == "youtube"
    assert result.media_id == "xyz987"
    assert str(result.cover_image_url) == "https://cdn.example.com/youtube-thumb.jpg"
    assert str(result.video_url) == "https://cdn.example.com/youtube-video.mp4"


@pytest.mark.anyio
async def test_scrape_rejects_unsupported_url() -> None:
    service, _, _, _ = build_service()

    with pytest.raises(HTTPException) as exc_info:
        await service.scrape(MediaScrapeRequest(url="https://example.com/video/123"))

    assert exc_info.value.status_code == 422
    assert (
        exc_info.value.detail
        == "URL must point to an Instagram Reel, TikTok video, or YouTube Short."
    )
