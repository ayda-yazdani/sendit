from fastapi import APIRouter, Depends

from app.dependencies import (
    get_instagram_reel_scraper_service,
    get_tiktok_video_scraper_service,
    get_verified_user,
    get_youtube_shorts_scraper_service,
)
from app.schemas.auth import SupabaseUser
from app.schemas.media import MediaScrapeRequest, MediaScrapeResponse
from app.services.instagram import InstagramReelScraperService
from app.services.media import MediaScraperService
from app.services.tiktok import TikTokVideoScraperService
from app.services.youtube import YouTubeShortsScraperService

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/scrape", response_model=MediaScrapeResponse)
async def scrape_media(
    payload: MediaScrapeRequest,
    _: SupabaseUser = Depends(get_verified_user),
    instagram_service: InstagramReelScraperService = Depends(
        get_instagram_reel_scraper_service
    ),
    tiktok_service: TikTokVideoScraperService = Depends(
        get_tiktok_video_scraper_service
    ),
    youtube_service: YouTubeShortsScraperService = Depends(
        get_youtube_shorts_scraper_service
    ),
) -> MediaScrapeResponse:
    scraper_service = MediaScraperService(
        instagram_service=instagram_service,
        tiktok_service=tiktok_service,
        youtube_service=youtube_service,
    )
    return await scraper_service.scrape(payload)
