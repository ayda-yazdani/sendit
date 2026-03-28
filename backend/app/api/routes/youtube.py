from fastapi import APIRouter, Depends

from app.dependencies import get_verified_user, get_youtube_shorts_scraper_service
from app.schemas.auth import SupabaseUser
from app.schemas.youtube import YouTubeShortScrapeRequest, YouTubeShortScrapeResponse
from app.services.youtube import YouTubeShortsScraperService

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.post("/shorts/scrape", response_model=YouTubeShortScrapeResponse)
async def scrape_youtube_short(
    payload: YouTubeShortScrapeRequest,
    _: SupabaseUser = Depends(get_verified_user),
    scraper_service: YouTubeShortsScraperService = Depends(
        get_youtube_shorts_scraper_service
    ),
) -> YouTubeShortScrapeResponse:
    return await scraper_service.scrape_short(payload)
