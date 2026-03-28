import os

from fastapi import APIRouter, Depends, Request, Response, status

from app.config import Settings, get_settings
from app.dependencies import get_access_token, get_supabase_auth_service
from app.schemas.auth import (
    AuthResponse,
    RefreshSessionRequest,
    SignInRequest,
    SignUpRequest,
    SupabaseConfigCheckResponse,
    SupabaseRuntimeInfoResponse,
    UserResponse,
)
from app.services.supabase_auth import SupabaseAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/runtime", response_model=SupabaseRuntimeInfoResponse)
async def supabase_runtime_info(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SupabaseRuntimeInfoResponse:
    return SupabaseRuntimeInfoResponse(
        api_base_url=str(request.base_url).rstrip("/"),
        supabase_url=settings.supabase_url,
        auth_url=settings.supabase_auth_url,
        key_present=bool(settings.supabase_key),
        key_name=(
            "SUPABASE_PUBLISHABLE_KEY"
            if os.getenv("SUPABASE_PUBLISHABLE_KEY")
            else "SUPABASE_ANON_KEY"
        ),
    )


@router.get("/config-check", response_model=SupabaseConfigCheckResponse)
async def check_supabase_config(
    auth_service: SupabaseAuthService = Depends(get_supabase_auth_service),
) -> SupabaseConfigCheckResponse:
    return await auth_service.check_configuration()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(
    payload: SignUpRequest,
    auth_service: SupabaseAuthService = Depends(get_supabase_auth_service),
) -> AuthResponse:
    return await auth_service.sign_up(payload)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: SignInRequest,
    auth_service: SupabaseAuthService = Depends(get_supabase_auth_service),
) -> AuthResponse:
    return await auth_service.sign_in(payload)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_session(
    payload: RefreshSessionRequest,
    auth_service: SupabaseAuthService = Depends(get_supabase_auth_service),
) -> AuthResponse:
    return await auth_service.refresh_session(payload)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    access_token: str = Depends(get_access_token),
    auth_service: SupabaseAuthService = Depends(get_supabase_auth_service),
) -> UserResponse:
    return await auth_service.get_current_user(access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    access_token: str = Depends(get_access_token),
    auth_service: SupabaseAuthService = Depends(get_supabase_auth_service),
) -> Response:
    await auth_service.sign_out(access_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
