from fastapi import APIRouter, Depends

from app.dependencies import get_tiktok_video_scraper_service, get_verified_user
from app.schemas.auth import SupabaseUser
from app.schemas.tiktok import TikTokVideoScrapeRequest, TikTokVideoScrapeResponse
from app.services.tiktok import TikTokVideoScraperService

router = APIRouter(prefix="/tiktok", tags=["tiktok"])


@router.post("/videos/scrape", response_model=TikTokVideoScrapeResponse)
async def scrape_tiktok_video(
    payload: TikTokVideoScrapeRequest,
    _: SupabaseUser = Depends(get_verified_user),
    scraper_service: TikTokVideoScraperService = Depends(
        get_tiktok_video_scraper_service
    ),
) -> TikTokVideoScrapeResponse:
    return await scraper_service.scrape_video(payload)
