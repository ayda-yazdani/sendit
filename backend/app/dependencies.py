from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.schemas.auth import SupabaseUser
from app.services.instagram import InstagramReelScraperService
from app.services.media_scrape_history import MediaScrapeHistoryService
from app.services.supabase_auth import SupabaseAuthService
from app.services.tiktok import TikTokVideoScraperService
from app.services.video_frames import VideoFrameService
from app.services.youtube import YouTubeShortsScraperService
from app.services.boards import BoardsService
from app.services.user_profiles import UserProfilesService

bearer_scheme = HTTPBearer(auto_error=False)


def get_supabase_auth_service(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SupabaseAuthService:
    return SupabaseAuthService(
        http_client=request.app.state.http_client,
        settings=settings,
    )


def get_instagram_reel_scraper_service(
    request: Request,
) -> InstagramReelScraperService:
    return InstagramReelScraperService(
        http_client=request.app.state.http_client,
        frame_service=VideoFrameService(),
    )


def get_tiktok_video_scraper_service(
    request: Request,
) -> TikTokVideoScraperService:
    return TikTokVideoScraperService(
        http_client=request.app.state.http_client,
        frame_service=VideoFrameService(),
    )


def get_youtube_shorts_scraper_service(
    request: Request,
) -> YouTubeShortsScraperService:
    return YouTubeShortsScraperService(
        http_client=request.app.state.http_client,
        frame_service=VideoFrameService(),
    )


def get_boards_service(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> BoardsService:
    return BoardsService(
        http_client=request.app.state.http_client,
        settings=settings,
    )


def get_user_profiles_service(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> UserProfilesService:
    return UserProfilesService(
        http_client=request.app.state.http_client,
        settings=settings,
    )


def get_media_scrape_history_service(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> MediaScrapeHistoryService:
    return MediaScrapeHistoryService(
        http_client=request.app.state.http_client,
        settings=settings,
    )


def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


async def get_current_user(
    access_token: str = Depends(get_access_token),
    auth_service: SupabaseAuthService = Depends(get_supabase_auth_service),
) -> SupabaseUser:
    return (await auth_service.get_current_user(access_token)).user


async def get_verified_user(
    user: SupabaseUser = Depends(get_current_user),
) -> SupabaseUser:
    if user.is_anonymous:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anonymous users cannot access this resource.",
        )

    if user.email_confirmed_at or user.phone_confirmed_at or user.confirmed_at:
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User must have a verified email or phone to access this resource.",
    )
