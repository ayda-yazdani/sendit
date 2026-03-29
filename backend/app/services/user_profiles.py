import httpx
from fastapi import HTTPException, status
import uuid
from datetime import datetime

from app.config import Settings
from app.schemas.boards import (
    UserProfileResponse,
    UserProfileCreateRequest,
    UserProfileUpdateRequest,
)


class UserProfilesService:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings
        self._supabase_url = str(settings.supabase_url).rstrip("/")
        self._headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
        }

    async def get_user_profile(self, device_id: str) -> UserProfileResponse:
        """Fetch a user's profile by device_id."""
        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/user_profiles",
            params={"device_id": f"eq.{device_id}"},
            headers=self._headers,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch user profile.",
            )

        data = response.json()
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found.",
            )

        return UserProfileResponse(**data[0])

    async def create_user_profile(
        self, device_id: str, payload: UserProfileCreateRequest
    ) -> UserProfileResponse:
        """Create a new user profile."""
        # Check if profile already exists
        check_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/user_profiles",
            params={"device_id": f"eq.{device_id}"},
            headers=self._headers,
        )

        if check_response.status_code == 200:
            data = check_response.json()
            if data and len(data) > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User profile already exists.",
                )

        # Create new profile
        now = datetime.utcnow().isoformat()
        profile_data = {
            "id": str(uuid.uuid4()),
            "device_id": device_id,
            "display_name": payload.display_name,
            "avatar_url": payload.avatar_url,
            "bio": payload.bio,
            "created_at": now,
            "updated_at": now,
        }

        response = await self._http_client.post(
            f"{self._supabase_url}/rest/v1/user_profiles",
            json=profile_data,
            headers=self._headers,
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not create user profile.",
            )

        result_data = response.json()
        if isinstance(result_data, list) and len(result_data) > 0:
            return UserProfileResponse(**result_data[0])

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not parse profile response.",
        )

    async def update_user_profile(
        self, device_id: str, payload: UserProfileUpdateRequest
    ) -> UserProfileResponse:
        """Update a user's profile."""
        # Get existing profile first
        profile_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/user_profiles",
            params={"device_id": f"eq.{device_id}"},
            headers=self._headers,
        )

        if profile_response.status_code != 200 or not profile_response.json():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found.",
            )

        existing_profile = profile_response.json()[0]

        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if payload.display_name is not None:
            update_data["display_name"] = payload.display_name
        if payload.avatar_url is not None:
            update_data["avatar_url"] = payload.avatar_url
        if payload.bio is not None:
            update_data["bio"] = payload.bio

        if len(update_data) == 1:  # Only updated_at
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            )

        response = await self._http_client.patch(
            f"{self._supabase_url}/rest/v1/user_profiles",
            params={"id": f"eq.{existing_profile['id']}"},
            json=update_data,
            headers=self._headers,
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not update user profile.",
            )

        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return UserProfileResponse(**data[0])

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not parse profile response.",
        )

    async def delete_user_profile(self, device_id: str) -> dict:
        """Delete a user's profile."""
        # Get profile first
        profile_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/user_profiles",
            params={"device_id": f"eq.{device_id}"},
            headers=self._headers,
        )

        if profile_response.status_code != 200 or not profile_response.json():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found.",
            )

        existing_profile = profile_response.json()[0]

        response = await self._http_client.delete(
            f"{self._supabase_url}/rest/v1/user_profiles",
            params={"id": f"eq.{existing_profile['id']}"},
            headers=self._headers,
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not delete user profile.",
            )

        return {"success": True, "message": "User profile successfully deleted."}
