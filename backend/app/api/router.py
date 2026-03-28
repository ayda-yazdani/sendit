from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.instagram import router as instagram_router
from app.api.routes.media import router as media_router
from app.api.routes.tiktok import router as tiktok_router
from app.api.routes.tester import router as tester_router
from app.api.routes.youtube import router as youtube_router
from app.api.routes.boards import router as boards_router
from app.api.routes.user_profiles import router as user_profiles_router

api_router = APIRouter()
api_router.include_router(tester_router)
api_router.include_router(auth_router)
api_router.include_router(media_router)
api_router.include_router(instagram_router)
api_router.include_router(tiktok_router)
api_router.include_router(youtube_router)
api_router.include_router(boards_router)
api_router.include_router(user_profiles_router)
