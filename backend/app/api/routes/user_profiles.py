from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_verified_user, get_user_profiles_service
from app.schemas.auth import SupabaseUser
from app.schemas.boards import (
    UserProfileResponse,
    UserProfileCreateRequest,
    UserProfileUpdateRequest,
)
from app.services.user_profiles import UserProfilesService


router = APIRouter(prefix="/profile", tags=["user-profile"])


# ===== USER PROFILE ENDPOINTS =====


@router.get(
    "",
    response_model=UserProfileResponse,
)
async def get_current_user_profile(
    user: SupabaseUser = Depends(get_verified_user),
    service: UserProfilesService = Depends(get_user_profiles_service),
) -> UserProfileResponse:
    """
    Get the current user's profile.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    device_id = user.id
    return await service.get_user_profile(device_id=device_id)


@router.post(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user_profile(
    payload: UserProfileCreateRequest,
    user: SupabaseUser = Depends(get_verified_user),
    service: UserProfilesService = Depends(get_user_profiles_service),
) -> UserProfileResponse:
    """
    Create a new user profile.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    - Body: UserProfileCreateRequest with display_name and optional avatar_url and bio
    """
    device_id = user.id
    return await service.create_user_profile(device_id=device_id, payload=payload)


@router.patch(
    "",
    response_model=UserProfileResponse,
)
async def update_user_profile(
    payload: UserProfileUpdateRequest,
    user: SupabaseUser = Depends(get_verified_user),
    service: UserProfilesService = Depends(get_user_profiles_service),
) -> UserProfileResponse:
    """
    Update the current user's profile.
    
    Allows updating display_name, avatar_url, and/or bio.
    Any fields not provided will remain unchanged.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    - Body: UserProfileUpdateRequest with fields to update
    """
    device_id = user.id
    return await service.update_user_profile(device_id=device_id, payload=payload)


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
)
async def delete_user_profile(
    user: SupabaseUser = Depends(get_verified_user),
    service: UserProfilesService = Depends(get_user_profiles_service),
) -> dict:
    """
    Delete the current user's profile.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    device_id = user.id
    return await service.delete_user_profile(device_id=device_id)


@router.get(
    "/public/{device_id}",
    response_model=UserProfileResponse,
)
async def get_public_user_profile(
    device_id: str,
    _: SupabaseUser = Depends(get_verified_user),
    service: UserProfilesService = Depends(get_user_profiles_service),
) -> UserProfileResponse:
    """
    Get another user's public profile.
    
    This is a public endpoint — all board members can view each other's profiles.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    return await service.get_user_profile(device_id=device_id)
