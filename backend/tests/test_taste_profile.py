from collections.abc import Generator
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_boards_service, get_supabase_auth_service
from app.main import app
from app.schemas.auth import SupabaseSession, SupabaseUser, UserResponse
from app.schemas.boards import (
    TasteProfileResponse,
    TasteProfileSyncRequest,
    TasteProfileUpdateRequest,
)
from app.services.boards import BoardsService


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


class StubBoardsServiceTasteProfile:
    """Mock boards service with taste profile methods."""

    def __init__(self) -> None:
        self.get_taste_profile_calls: list[str] = []
        self.sync_taste_profile_calls: list[tuple[str, TasteProfileSyncRequest]] = []
        self.update_taste_profile_calls: list[tuple[str, TasteProfileUpdateRequest]] = []

    async def get_taste_profile(self, board_id: str) -> TasteProfileResponse:
        self.get_taste_profile_calls.append(board_id)
        return TasteProfileResponse(
            id="profile-123",
            board_id=board_id,
            activity_types=["dining", "nightlife"],
            aesthetic_register=["underground", "casual"],
            food_preferences=["japanese", "thai"],
            location_patterns=["east london", "shoreditch"],
            price_range="£15-30",
            vibe_tags=["dark humour", "intimate"],
            identity_label="Underground East London Vibes",
            reel_count=8,
            updated_at=datetime.fromisoformat("2026-03-28T12:00:00"),
            created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
        )

    async def sync_taste_profile(
        self, board_id: str, payload: TasteProfileSyncRequest
    ) -> TasteProfileResponse:
        self.sync_taste_profile_calls.append((board_id, payload))
        return TasteProfileResponse(
            id="profile-456",
            board_id=board_id,
            activity_types=["events", "venues", "dining"],
            aesthetic_register=["upscale", "intimate"],
            food_preferences=["italian", "french"],
            location_patterns=["central london", "west end"],
            price_range="£30-50",
            vibe_tags=["high energy", "sophisticated"],
            identity_label="Sophisticated Central London Experiences",
            reel_count=12,
            updated_at=datetime.fromisoformat("2026-03-28T13:00:00"),
            created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
        )

    async def update_taste_profile(
        self, board_id: str, payload: TasteProfileUpdateRequest
    ) -> TasteProfileResponse:
        self.update_taste_profile_calls.append((board_id, payload))
        return TasteProfileResponse(
            id="profile-789",
            board_id=board_id,
            activity_types=payload.activity_types or ["events", "dining"],
            aesthetic_register=payload.aesthetic_register or ["casual"],
            food_preferences=payload.food_preferences or [],
            location_patterns=payload.location_patterns or ["london"],
            price_range=payload.price_range or "£20-40",
            vibe_tags=payload.vibe_tags or ["fun"],
            identity_label=payload.identity_label or "Updated Group Vibe",
            reel_count=15,
            updated_at=datetime.fromisoformat("2026-03-28T14:00:00"),
            created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
        )


class StubBoardsServiceProfileNotFound(StubBoardsServiceTasteProfile):
    async def get_taste_profile(self, board_id: str) -> TasteProfileResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taste profile not found for this board.",
        )


class StubBoardsServiceUpdateFails(StubBoardsServiceTasteProfile):
    async def update_taste_profile(
        self, board_id: str, payload: TasteProfileUpdateRequest
    ) -> TasteProfileResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not update taste profile.",
        )


@pytest.fixture
def stub_auth_service() -> StubSupabaseAuthService:
    return StubSupabaseAuthService()


@pytest.fixture
def stub_boards_service() -> StubBoardsServiceTasteProfile:
    return StubBoardsServiceTasteProfile()


@pytest.fixture
def client(
    stub_auth_service: StubSupabaseAuthService,
    stub_boards_service: StubBoardsServiceTasteProfile,
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_supabase_auth_service] = lambda: stub_auth_service
    app.dependency_overrides[get_boards_service] = lambda: stub_boards_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ===== GET TASTE PROFILE TESTS =====


class TestGetTasteProfile:
    def test_get_taste_profile_success(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test successfully retrieving a taste profile."""
        response = client.get(
            "/api/v1/boards/board-123/taste-profile",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "profile-123"
        assert data["board_id"] == "board-123"
        assert "dining" in data["activity_types"]
        assert "nightlife" in data["activity_types"]
        assert "japanese" in data["food_preferences"]
        assert data["price_range"] == "£15-30"
        assert data["reel_count"] == 8
        assert "Underground" in data["identity_label"]

        # Verify service was called
        assert len(stub_boards_service.get_taste_profile_calls) == 1
        assert stub_boards_service.get_taste_profile_calls[0] == "board-123"

    def test_get_taste_profile_not_found(self, client: TestClient) -> None:
        """Test error when taste profile doesn't exist."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceProfileNotFound()
        )
        response = client.get(
            "/api/v1/boards/board-999/taste-profile",
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_taste_profile_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.get("/api/v1/boards/board-123/taste-profile")

        assert response.status_code == 401

    def test_get_taste_profile_with_all_fields(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test that response includes all taste profile fields."""
        response = client.get(
            "/api/v1/boards/board-123/taste-profile",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "id",
            "board_id",
            "activity_types",
            "aesthetic_register",
            "food_preferences",
            "location_patterns",
            "price_range",
            "vibe_tags",
            "identity_label",
            "reel_count",
            "updated_at",
            "created_at",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"


# ===== SYNC TASTE PROFILE TESTS =====


class TestSyncTasteProfile:
    def test_sync_taste_profile_success(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test successfully syncing/generating a taste profile."""
        response = client.post(
            "/api/v1/boards/board-123/taste-profile/sync",
            json={"force": False},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "profile-456"
        assert data["board_id"] == "board-123"
        assert "events" in data["activity_types"]
        assert "venues" in data["activity_types"]
        assert "dining" in data["activity_types"]
        assert "italian" in data["food_preferences"]
        assert data["reel_count"] == 12
        assert "Sophisticated" in data["identity_label"]

        # Verify service was called with correct payload
        assert len(stub_boards_service.sync_taste_profile_calls) == 1
        board_id, payload = stub_boards_service.sync_taste_profile_calls[0]
        assert board_id == "board-123"
        assert payload.force is False

    def test_sync_taste_profile_with_force(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test syncing with force flag to ignore cache."""
        response = client.post(
            "/api/v1/boards/board-456/taste-profile/sync",
            json={"force": True},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert len(stub_boards_service.sync_taste_profile_calls) == 1
        board_id, payload = stub_boards_service.sync_taste_profile_calls[0]
        assert payload.force is True

    def test_sync_taste_profile_default_payload(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test sync with empty/default payload."""
        response = client.post(
            "/api/v1/boards/board-789/taste-profile/sync",
            json={},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert len(stub_boards_service.sync_taste_profile_calls) == 1
        board_id, payload = stub_boards_service.sync_taste_profile_calls[0]
        assert payload.force is False

    def test_sync_taste_profile_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.post(
            "/api/v1/boards/board-123/taste-profile/sync",
            json={"force": False},
        )

        assert response.status_code == 401

    def test_sync_taste_profile_multiple_activity_types(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test that sync returns multiple activity types."""
        response = client.post(
            "/api/v1/boards/board-multi/taste-profile/sync",
            json={"force": False},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["activity_types"], list)
        assert len(data["activity_types"]) > 1


# ===== UPDATE TASTE PROFILE TESTS =====


class TestUpdateTasteProfile:
    def test_update_taste_profile_single_field(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test updating a single field in taste profile."""
        response = client.patch(
            "/api/v1/boards/board-123/taste-profile",
            json={"identity_label": "Trendy West London Crew"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["identity_label"] == "Trendy West London Crew"

        # Verify service was called
        assert len(stub_boards_service.update_taste_profile_calls) == 1

    def test_update_taste_profile_multiple_fields(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test updating multiple fields in taste profile."""
        response = client.patch(
            "/api/v1/boards/board-456/taste-profile",
            json={
                "activity_types": ["concerts", "festivals"],
                "price_range": "£40-60",
                "identity_label": "Festival Lovers",
            },
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert len(stub_boards_service.update_taste_profile_calls) == 1
        board_id, payload = stub_boards_service.update_taste_profile_calls[0]
        assert board_id == "board-456"
        assert payload.activity_types == ["concerts", "festivals"]
        assert payload.price_range == "£40-60"
        assert payload.identity_label == "Festival Lovers"

    def test_update_taste_profile_activity_types(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test updating activity types."""
        new_activities = ["sports", "outdoor", "fitness"]
        response = client.patch(
            "/api/v1/boards/board-789/taste-profile",
            json={"activity_types": new_activities},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        board_id, payload = stub_boards_service.update_taste_profile_calls[0]
        assert payload.activity_types == new_activities

    def test_update_taste_profile_food_preferences(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test updating food preferences."""
        new_prefs = ["korean", "vietnamese", "chinese"]
        response = client.patch(
            "/api/v1/boards/board-food/taste-profile",
            json={"food_preferences": new_prefs},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        board_id, payload = stub_boards_service.update_taste_profile_calls[0]
        assert payload.food_preferences == new_prefs

    def test_update_taste_profile_location_patterns(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test updating location patterns."""
        new_locations = ["north london", "hampstead", "belsize park"]
        response = client.patch(
            "/api/v1/boards/board-location/taste-profile",
            json={"location_patterns": new_locations},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        board_id, payload = stub_boards_service.update_taste_profile_calls[0]
        assert payload.location_patterns == new_locations

    def test_update_taste_profile_vibe_tags(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test updating vibe tags."""
        new_vibes = ["sophisticated", "artsy", "bohemian"]
        response = client.patch(
            "/api/v1/boards/board-vibe/taste-profile",
            json={"vibe_tags": new_vibes},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        board_id, payload = stub_boards_service.update_taste_profile_calls[0]
        assert payload.vibe_tags == new_vibes

    def test_update_taste_profile_price_range(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test updating price range."""
        response = client.patch(
            "/api/v1/boards/board-price/taste-profile",
            json={"price_range": "£50+"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        board_id, payload = stub_boards_service.update_taste_profile_calls[0]
        assert payload.price_range == "£50+"

    def test_update_taste_profile_empty_payload(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test update with empty payload (no fields to update)."""
        response = client.patch(
            "/api/v1/boards/board-empty/taste-profile",
            json={},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert len(stub_boards_service.update_taste_profile_calls) == 1

    def test_update_taste_profile_fails(self, client: TestClient) -> None:
        """Test error when update fails."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceUpdateFails()
        )
        response = client.patch(
            "/api/v1/boards/board-err/taste-profile",
            json={"identity_label": "New Label"},
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 502
        assert "Could not update" in response.json()["detail"]

    def test_update_taste_profile_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.patch(
            "/api/v1/boards/board-123/taste-profile",
            json={"price_range": "£50+"},
        )

        assert response.status_code == 401


# ===== INTEGRATION TESTS =====


class TestTasteProfileIntegration:
    def test_get_after_sync(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test getting taste profile after syncing it."""
        # Sync profile
        sync_response = client.post(
            "/api/v1/boards/board-123/taste-profile/sync",
            json={"force": False},
            headers={"Authorization": "Bearer access-token"},
        )
        assert sync_response.status_code == 200
        sync_data = sync_response.json()

        # Get profile
        get_response = client.get(
            "/api/v1/boards/board-123/taste-profile",
            headers={"Authorization": "Bearer access-token"},
        )
        assert get_response.status_code == 200
        get_data = get_response.json()

        # Both requests should work
        assert sync_data["board_id"] == get_data["board_id"]

    def test_sync_then_update(
        self, client: TestClient, stub_boards_service: StubBoardsServiceTasteProfile
    ) -> None:
        """Test syncing then updating a taste profile."""
        # Sync
        sync_response = client.post(
            "/api/v1/boards/board-flow/taste-profile/sync",
            json={"force": False},
            headers={"Authorization": "Bearer access-token"},
        )
        assert sync_response.status_code == 200

        # Update
        update_response = client.patch(
            "/api/v1/boards/board-flow/taste-profile",
            json={"identity_label": "Refined Tastes"},
            headers={"Authorization": "Bearer access-token"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["identity_label"] == "Refined Tastes"

        # Verify both operations were called
        assert len(stub_boards_service.sync_taste_profile_calls) == 1
        assert len(stub_boards_service.update_taste_profile_calls) == 1
