from collections.abc import Generator
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_user_profiles_service, get_supabase_auth_service
from app.main import app
from app.schemas.auth import SupabaseSession, SupabaseUser, UserResponse
from app.schemas.boards import (
    UserProfileResponse,
    UserProfileCreateRequest,
    UserProfileUpdateRequest,
)
from app.services.user_profiles import UserProfilesService


class StubSupabaseAuthService:
    """Mock authentication service for testing."""

    async def get_current_user(self, access_token: str) -> UserResponse:
        return UserResponse(
            user=SupabaseUser(
                id="device-123",
                email="user@example.com",
                email_confirmed_at="2026-03-28T12:00:00Z",
            )
        )


class StubUserProfilesService:
    """Mock user profiles service for testing."""

    def __init__(self) -> None:
        self.get_user_profile_calls: list[str] = []
        self.create_user_profile_calls: list[tuple[str, UserProfileCreateRequest]] = []
        self.update_user_profile_calls: list[tuple[str, UserProfileUpdateRequest]] = []
        self.delete_user_profile_calls: list[str] = []

    async def get_user_profile(self, device_id: str) -> UserProfileResponse:
        self.get_user_profile_calls.append(device_id)
        return UserProfileResponse(
            id="profile-123",
            device_id=device_id,
            display_name="Alice Smith",
            avatar_url="https://example.com/alice.jpg",
            bio="Adventure seeker and food enthusiast",
            created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
            updated_at=datetime.fromisoformat("2026-03-28T12:00:00"),
        )

    async def create_user_profile(
        self, device_id: str, payload: UserProfileCreateRequest
    ) -> UserProfileResponse:
        self.create_user_profile_calls.append((device_id, payload))
        return UserProfileResponse(
            id="profile-456",
            device_id=device_id,
            display_name=payload.display_name,
            avatar_url=payload.avatar_url,
            bio=payload.bio,
            created_at=datetime.fromisoformat("2026-03-28T13:00:00"),
            updated_at=datetime.fromisoformat("2026-03-28T13:00:00"),
        )

    async def update_user_profile(
        self, device_id: str, payload: UserProfileUpdateRequest
    ) -> UserProfileResponse:
        self.update_user_profile_calls.append((device_id, payload))
        return UserProfileResponse(
            id="profile-789",
            device_id=device_id,
            display_name=payload.display_name or "Updated User",
            avatar_url=payload.avatar_url or "https://example.com/avatar.jpg",
            bio=payload.bio or "Updated bio",
            created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
            updated_at=datetime.fromisoformat("2026-03-28T14:00:00"),
        )

    async def delete_user_profile(self, device_id: str) -> dict:
        self.delete_user_profile_calls.append(device_id)
        return {"success": True, "message": "User profile successfully deleted."}


class StubUserProfilesServiceNotFound(StubUserProfilesService):
    async def get_user_profile(self, device_id: str) -> UserProfileResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )


class StubUserProfilesServiceConflict(StubUserProfilesService):
    async def create_user_profile(
        self, device_id: str, payload: UserProfileCreateRequest
    ) -> UserProfileResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User profile already exists.",
        )


class StubUserProfilesServiceUpdateFails(StubUserProfilesService):
    async def update_user_profile(
        self, device_id: str, payload: UserProfileUpdateRequest
    ) -> UserProfileResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not update user profile.",
        )


@pytest.fixture
def stub_auth_service() -> StubSupabaseAuthService:
    return StubSupabaseAuthService()


@pytest.fixture
def stub_user_profiles_service() -> StubUserProfilesService:
    return StubUserProfilesService()


@pytest.fixture
def client(
    stub_auth_service: StubSupabaseAuthService,
    stub_user_profiles_service: StubUserProfilesService,
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_supabase_auth_service] = lambda: stub_auth_service
    app.dependency_overrides[get_user_profiles_service] = lambda: stub_user_profiles_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ===== GET CURRENT USER PROFILE TESTS =====


class TestGetCurrentUserProfile:
    def test_get_current_user_profile_success(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test successfully retrieving current user's profile."""
        response = client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "profile-123"
        assert data["device_id"] == "device-123"
        assert data["display_name"] == "Alice Smith"
        assert data["avatar_url"] == "https://example.com/alice.jpg"
        assert "Adventure" in data["bio"]

        # Verify service was called with correct device_id
        assert len(stub_user_profiles_service.get_user_profile_calls) == 1
        assert stub_user_profiles_service.get_user_profile_calls[0] == "device-123"

    def test_get_current_user_profile_not_found(self, client: TestClient) -> None:
        """Test error when user profile doesn't exist."""
        app.dependency_overrides[get_user_profiles_service] = (
            lambda: StubUserProfilesServiceNotFound()
        )
        response = client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_current_user_profile_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.get("/api/v1/profile")

        assert response.status_code == 401

    def test_get_current_user_profile_with_all_fields(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test that response includes all user profile fields."""
        response = client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        required_fields = ["id", "device_id", "display_name", "avatar_url", "bio", "created_at", "updated_at"]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"


# ===== CREATE USER PROFILE TESTS =====


class TestCreateUserProfile:
    def test_create_user_profile_success(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test successfully creating a user profile."""
        response = client.post(
            "/api/v1/profile",
            json={
                "display_name": "Bob Johnson",
                "avatar_url": "https://example.com/bob.jpg",
                "bio": "Music lover",
            },
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "profile-456"
        assert data["device_id"] == "device-123"
        assert data["display_name"] == "Bob Johnson"
        assert data["avatar_url"] == "https://example.com/bob.jpg"
        assert data["bio"] == "Music lover"

        # Verify service was called with correct payload
        assert len(stub_user_profiles_service.create_user_profile_calls) == 1
        device_id, payload = stub_user_profiles_service.create_user_profile_calls[0]
        assert device_id == "device-123"
        assert payload.display_name == "Bob Johnson"

    def test_create_user_profile_minimal(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test creating profile with only required fields."""
        response = client.post(
            "/api/v1/profile",
            json={"display_name": "Charlie Brown"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "Charlie Brown"
        assert data["avatar_url"] is None
        assert data["bio"] is None

    def test_create_user_profile_already_exists(self, client: TestClient) -> None:
        """Test error when trying to create profile that already exists."""
        app.dependency_overrides[get_user_profiles_service] = (
            lambda: StubUserProfilesServiceConflict()
        )
        response = client.post(
            "/api/v1/profile",
            json={"display_name": "David"},
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_user_profile_missing_display_name(
        self, client: TestClient
    ) -> None:
        """Test error when display_name is missing."""
        response = client.post(
            "/api/v1/profile",
            json={"avatar_url": "https://example.com/avatar.jpg"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 422

    def test_create_user_profile_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.post(
            "/api/v1/profile",
            json={"display_name": "Eve"},
        )

        assert response.status_code == 401


# ===== UPDATE USER PROFILE TESTS =====


class TestUpdateUserProfile:
    def test_update_user_profile_display_name(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test updating user's display name."""
        response = client.patch(
            "/api/v1/profile",
            json={"display_name": "Alice Updated"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert response.json()["display_name"] == "Alice Updated"

        # Verify service was called
        assert len(stub_user_profiles_service.update_user_profile_calls) == 1

    def test_update_user_profile_avatar(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test updating user's avatar."""
        response = client.patch(
            "/api/v1/profile",
            json={"avatar_url": "https://example.com/new-avatar.jpg"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert response.json()["avatar_url"] == "https://example.com/new-avatar.jpg"

    def test_update_user_profile_bio(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test updating user's bio."""
        response = client.patch(
            "/api/v1/profile",
            json={"bio": "Updated bio text"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert response.json()["bio"] == "Updated bio text"

    def test_update_user_profile_all_fields(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test updating all user profile fields."""
        response = client.patch(
            "/api/v1/profile",
            json={
                "display_name": "New Name",
                "avatar_url": "https://example.com/new.jpg",
                "bio": "New bio",
            },
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert len(stub_user_profiles_service.update_user_profile_calls) == 1
        device_id, payload = stub_user_profiles_service.update_user_profile_calls[0]
        assert payload.display_name == "New Name"
        assert payload.avatar_url == "https://example.com/new.jpg"
        assert payload.bio == "New bio"

    def test_update_user_profile_empty_payload(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test update with empty payload."""
        response = client.patch(
            "/api/v1/profile",
            json={},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert len(stub_user_profiles_service.update_user_profile_calls) == 1

    def test_update_user_profile_fails(self, client: TestClient) -> None:
        """Test error when update fails."""
        app.dependency_overrides[get_user_profiles_service] = (
            lambda: StubUserProfilesServiceUpdateFails()
        )
        response = client.patch(
            "/api/v1/profile",
            json={"display_name": "New Name"},
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 502
        assert "Could not update" in response.json()["detail"]

    def test_update_user_profile_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.patch(
            "/api/v1/profile",
            json={"display_name": "New Name"},
        )

        assert response.status_code == 401


# ===== DELETE USER PROFILE TESTS =====


class TestDeleteUserProfile:
    def test_delete_user_profile_success(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test successfully deleting user profile."""
        response = client.delete(
            "/api/v1/profile",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify service was called
        assert len(stub_user_profiles_service.delete_user_profile_calls) == 1
        assert stub_user_profiles_service.delete_user_profile_calls[0] == "device-123"

    def test_delete_user_profile_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.delete("/api/v1/profile")

        assert response.status_code == 401


# ===== GET PUBLIC USER PROFILE TESTS =====


class TestGetPublicUserProfile:
    def test_get_public_user_profile_success(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test viewing another user's public profile."""
        response = client.get(
            "/api/v1/profile/public/device-456",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "display_name" in data

        # Verify service was called with correct device_id
        assert len(stub_user_profiles_service.get_user_profile_calls) == 1
        assert stub_user_profiles_service.get_user_profile_calls[0] == "device-456"

    def test_get_public_user_profile_not_found(self, client: TestClient) -> None:
        """Test error when public profile doesn't exist."""
        app.dependency_overrides[get_user_profiles_service] = (
            lambda: StubUserProfilesServiceNotFound()
        )
        response = client.get(
            "/api/v1/profile/public/nonexistent",
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_get_public_user_profile_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.get("/api/v1/profile/public/device-456")

        assert response.status_code == 401

    def test_get_public_user_profile_own_profile(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test viewing your own profile via public endpoint."""
        response = client.get(
            "/api/v1/profile/public/device-123",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert len(stub_user_profiles_service.get_user_profile_calls) == 1


# ===== INTEGRATION TESTS =====


class TestUserProfileIntegration:
    def test_create_then_get(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test creating a profile then retrieving it."""
        # Create
        create_response = client.post(
            "/api/v1/profile",
            json={"display_name": "Integration Test User"},
            headers={"Authorization": "Bearer access-token"},
        )
        assert create_response.status_code == 201

        # Get
        get_response = client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer access-token"},
        )
        assert get_response.status_code == 200

        # Verify both operations worked
        assert len(stub_user_profiles_service.create_user_profile_calls) == 1
        assert len(stub_user_profiles_service.get_user_profile_calls) == 1

    def test_create_then_update_then_get(
        self, client: TestClient, stub_user_profiles_service: StubUserProfilesService
    ) -> None:
        """Test full profile lifecycle: create, update, get."""
        # Create
        create_response = client.post(
            "/api/v1/profile",
            json={"display_name": "Original Name"},
            headers={"Authorization": "Bearer access-token"},
        )
        assert create_response.status_code == 201

        # Update
        update_response = client.patch(
            "/api/v1/profile",
            json={"display_name": "Updated Name", "bio": "New bio"},
            headers={"Authorization": "Bearer access-token"},
        )
        assert update_response.status_code == 200

        # Get
        get_response = client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer access-token"},
        )
        assert get_response.status_code == 200

        # Verify all operations
        assert len(stub_user_profiles_service.create_user_profile_calls) == 1
        assert len(stub_user_profiles_service.update_user_profile_calls) == 1
        assert len(stub_user_profiles_service.get_user_profile_calls) == 1
