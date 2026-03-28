from urllib.parse import urlparse

from fastapi import HTTPException, status

from app.schemas.instagram import InstagramReelScrapeRequest, InstagramReelScrapeResponse
from app.schemas.media import MediaScrapeRequest, MediaScrapeResponse, MediaUser
from app.schemas.tiktok import TikTokVideoScrapeRequest, TikTokVideoScrapeResponse
from app.schemas.youtube import YouTubeShortScrapeRequest, YouTubeShortScrapeResponse
from app.services.instagram import InstagramReelScraperService
from app.services.tiktok import TikTokVideoScraperService
from app.services.youtube import YouTubeShortsScraperService

INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
TIKTOK_HOSTS = {
    "tiktok.com",
    "www.tiktok.com",
    "m.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
}
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}


class MediaScraperService:
    def __init__(
        self,
        instagram_service: InstagramReelScraperService,
        tiktok_service: TikTokVideoScraperService,
        youtube_service: YouTubeShortsScraperService,
    ) -> None:
        self._instagram_service = instagram_service
        self._tiktok_service = tiktok_service
        self._youtube_service = youtube_service

    async def scrape(self, payload: MediaScrapeRequest) -> MediaScrapeResponse:
        platform = self.detect_platform(str(payload.url))
        if platform is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="URL must point to an Instagram Reel, TikTok video, or YouTube Short.",
            )

        if platform == "instagram":
            result = await self._instagram_service.scrape_reel(
                InstagramReelScrapeRequest(url=payload.url)
            )
            return self._normalize_instagram(result)

        if platform == "tiktok":
            result = await self._tiktok_service.scrape_video(
                TikTokVideoScrapeRequest(url=payload.url)
            )
            return self._normalize_tiktok(result)

        result = await self._youtube_service.scrape_short(
            YouTubeShortScrapeRequest(url=payload.url)
        )
        return self._normalize_youtube(result)

    def detect_platform(self, url: str) -> str | None:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path

        if host in INSTAGRAM_HOSTS and path.startswith("/reel/"):
            return "instagram"

        if host in TIKTOK_HOSTS:
            if host in {"vm.tiktok.com", "vt.tiktok.com"} or "/video/" in path:
                return "tiktok"

        if host in YOUTUBE_HOSTS and path.startswith("/shorts/"):
            return "youtube"

        return None

    def _normalize_instagram(
        self, payload: InstagramReelScrapeResponse
    ) -> MediaScrapeResponse:
        return MediaScrapeResponse(
            platform="instagram",
            requested_url=payload.requested_url,
            resolved_url=payload.resolved_url,
            canonical_url=payload.canonical_url,
            media_id=payload.reel_id,
            title=payload.title,
            description=payload.description,
            cover_image_url=payload.cover_image_url,
            video_url=payload.video_url,
            embed_url=payload.embed_url,
            post_date=payload.post_date,
            duration=payload.duration,
            user=self._normalize_user(
                payload.user.name if payload.user else None,
                payload.user.username if payload.user else None,
                payload.user.profile_url if payload.user else None,
            ),
        )

    def _normalize_tiktok(
        self, payload: TikTokVideoScrapeResponse
    ) -> MediaScrapeResponse:
        return MediaScrapeResponse(
            platform="tiktok",
            requested_url=payload.requested_url,
            resolved_url=payload.resolved_url,
            canonical_url=payload.canonical_url,
            media_id=payload.video_id,
            title=payload.title,
            description=payload.description,
            cover_image_url=payload.cover_image_url,
            video_url=payload.video_url,
            embed_url=payload.embed_url,
            post_date=payload.post_date,
            duration=payload.duration,
            user=self._normalize_user(
                payload.user.name if payload.user else None,
                payload.user.username if payload.user else None,
                payload.user.profile_url if payload.user else None,
            ),
        )

    def _normalize_youtube(
        self, payload: YouTubeShortScrapeResponse
    ) -> MediaScrapeResponse:
        username = None
        profile_url = None
        name = None
        if payload.user:
            name = payload.user.name
            username = payload.user.handle
            profile_url = payload.user.channel_url

        return MediaScrapeResponse(
            platform="youtube",
            requested_url=payload.requested_url,
            resolved_url=payload.resolved_url,
            canonical_url=payload.canonical_url,
            media_id=payload.short_id,
            title=payload.title,
            description=payload.description,
            cover_image_url=payload.cover_image_url,
            video_url=payload.video_url,
            embed_url=payload.embed_url,
            post_date=payload.post_date,
            duration=payload.duration,
            user=self._normalize_user(name, username, profile_url),
        )

    def _normalize_user(
        self,
        name: str | None,
        username: str | None,
        profile_url: str | None | object,
    ) -> MediaUser | None:
        if name is None and username is None and profile_url is None:
            return None

        return MediaUser(
            name=name,
            username=username,
            profile_url=profile_url,
        )
