from fastapi import APIRouter, Depends

from app.dependencies import get_instagram_reel_scraper_service, get_verified_user
from app.schemas.auth import SupabaseUser
from app.schemas.instagram import (
    InstagramReelScrapeRequest,
    InstagramReelScrapeResponse,
)
from app.services.instagram import InstagramReelScraperService

router = APIRouter(prefix="/instagram", tags=["instagram"])


@router.post("/reels/scrape", response_model=InstagramReelScrapeResponse)
async def scrape_instagram_reel(
    payload: InstagramReelScrapeRequest,
    _: SupabaseUser = Depends(get_verified_user),
    scraper_service: InstagramReelScraperService = Depends(
        get_instagram_reel_scraper_service
    ),
) -> InstagramReelScrapeResponse:
    return await scraper_service.scrape_reel(payload)
