from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.instagram import router as instagram_router
from app.api.routes.tiktok import router as tiktok_router
from app.api.routes.youtube import router as youtube_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(instagram_router)
api_router.include_router(tiktok_router)
api_router.include_router(youtube_router)
