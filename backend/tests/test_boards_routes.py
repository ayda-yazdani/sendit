from collections.abc import Generator
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_boards_service, get_supabase_auth_service
from app.main import app
from app.schemas.auth import SupabaseSession, SupabaseUser, UserResponse, AuthResponse
from app.schemas.boards import (
    ReelCreateRequest,
    ReelResponse,
    ReelsListResponse,
    ReelDeleteResponse,
)
from app.services.boards import BoardsService


class StubSupabaseAuthService:
    """Mock authentication service for testing."""

    async def get_current_user(self, access_token: str) -> UserResponse:
        return UserResponse(
            user=SupabaseUser(
                id="user-123",
                email="user@example.com",
                email_confirmed_at="2026-03-28T12:00:00Z",
            )
        )


class StubBoardsService:
    """Mock boards service for testing."""

    def __init__(self) -> None:
        self.add_reel_calls: list[tuple[str, str, ReelCreateRequest]] = []
        self.list_reels_calls: list[tuple[str, int, int]] = []
        self.delete_reel_calls: list[tuple[str, str]] = []

    async def add_reel_to_board(
        self,
        board_id: str,
        member_id: str,
        payload: ReelCreateRequest,
    ) -> ReelResponse:
        self.add_reel_calls.append((board_id, member_id, payload))
        return ReelResponse(
            id="reel-123",
            board_id=board_id,
            added_by=member_id,
            url=payload.url,
            platform=payload.platform,
            classification="real_event",
            extraction_data={
                "type": "real_event",
                "venue_name": "Example Venue",
                "location": "London, UK",
            },
            created_at=datetime.fromisoformat("2026-03-28T12:00:00"),
        )

    async def list_reels_in_board(
        self, board_id: str, limit: int = 100, offset: int = 0
    ) -> ReelsListResponse:
        self.list_reels_calls.append((board_id, limit, offset))
        return ReelsListResponse(
            reels=[
                ReelResponse(
                    id="reel-1",
                    board_id=board_id,
                    added_by="user-123",
                    url="https://www.instagram.com/reel/abc123/",
                    platform="instagram",
                    classification="real_event",
                    extraction_data={"type": "real_event"},
                    created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
                ),
                ReelResponse(
                    id="reel-2",
                    board_id=board_id,
                    added_by="user-456",
                    url="https://www.tiktok.com/@creator/video/9876543210",
                    platform="tiktok",
                    classification="vibe_inspiration",
                    extraction_data={"type": "vibe_inspiration"},
                    created_at=datetime.fromisoformat("2026-03-28T11:00:00"),
                ),
            ],
            total=2,
            board_id=board_id,
        )

    async def delete_reel_from_board(self, board_id: str, reel_id: str) -> dict:
        self.delete_reel_calls.append((board_id, reel_id))
        return {
            "success": True,
            "message": "Reel successfully deleted from board.",
        }


class StubBoardsServiceNotFound(StubBoardsService):
    """Mock boards service that simulates board not found."""

    async def add_reel_to_board(
        self,
        board_id: str,
        member_id: str,
        payload: ReelCreateRequest,
    ) -> ReelResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found.",
        )


class StubBoardsServiceNotMember(StubBoardsService):
    """Mock boards service that simulates user not member."""

    async def add_reel_to_board(
        self,
        board_id: str,
        member_id: str,
        payload: ReelCreateRequest,
    ) -> ReelResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this board.",
        )


class StubBoardsServiceDuplicate(StubBoardsService):
    """Mock boards service that simulates duplicate reel."""

    async def add_reel_to_board(
        self,
        board_id: str,
        member_id: str,
        payload: ReelCreateRequest,
    ) -> ReelResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This reel already exists in this board.",
        )


@pytest.fixture
def stub_auth_service() -> StubSupabaseAuthService:
    return StubSupabaseAuthService()


@pytest.fixture
def stub_boards_service() -> StubBoardsService:
    return StubBoardsService()


@pytest.fixture
def client(
    stub_auth_service: StubSupabaseAuthService,
    stub_boards_service: StubBoardsService,
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_supabase_auth_service] = lambda: stub_auth_service
    app.dependency_overrides[get_boards_service] = lambda: stub_boards_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Tests for GET /boards/{board_id}/reels
class TestListBoardReels:
    def test_list_reels_success(self, client: TestClient) -> None:
        """Test successfully listing reels in a board."""
        response = client.get(
            "/api/v1/boards/board-123/reels",
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["board_id"] == "board-123"
        assert len(data["reels"]) == 2
        assert data["total"] == 2
        assert data["reels"][0]["id"] == "reel-1"
        assert data["reels"][0]["platform"] == "instagram"
        assert data["reels"][1]["id"] == "reel-2"
        assert data["reels"][1]["platform"] == "tiktok"

    def test_list_reels_with_pagination(self, client: TestClient) -> None:
        """Test listing reels with limit and offset."""
        response = client.get(
            "/api/v1/boards/board-123/reels?limit=10&offset=5",
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["board_id"] == "board-123"

    def test_list_reels_missing_member_id(self, client: TestClient) -> None:
        """Test error when member_id header is missing."""
        response = client.get(
            "/api/v1/boards/board-123/reels",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 400

    def test_list_reels_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.get(
            "/api/v1/boards/board-123/reels",
            headers={"X-Member-ID": "user-123"},
        )

        assert response.status_code == 401


# Tests for POST /boards/{board_id}/reels
class TestAddReelToBoard:
    def test_add_reel_success(
        self,
        client: TestClient,
        stub_boards_service: StubBoardsService,
    ) -> None:
        """Test successfully adding a reel to a board."""
        response = client.post(
            "/api/v1/boards/board-123/reels",
            json={
                "url": "https://www.instagram.com/reel/abc123/",
                "platform": "instagram",
            },
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-123"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Reel added to board."
        assert data["reel"]["id"] == "reel-123"
        assert data["reel"]["platform"] == "instagram"
        assert data["reel"]["url"] == "https://www.instagram.com/reel/abc123/"

        # Verify the service was called correctly
        assert len(stub_boards_service.add_reel_calls) == 1
        board_id, member_id, payload = stub_boards_service.add_reel_calls[0]
        assert board_id == "board-123"
        assert member_id == "user-123"
        assert payload.url == "https://www.instagram.com/reel/abc123/"
        assert payload.platform == "instagram"

    def test_add_tiktok_reel(self, client: TestClient) -> None:
        """Test adding a TikTok reel."""
        response = client.post(
            "/api/v1/boards/board-456/reels",
            json={
                "url": "https://www.tiktok.com/@creator/video/9876543210",
                "platform": "tiktok",
            },
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-456"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["reel"]["platform"] == "tiktok"

    def test_add_youtube_reel(self, client: TestClient) -> None:
        """Test adding a YouTube short."""
        response = client.post(
            "/api/v1/boards/board-789/reels",
            json={
                "url": "https://www.youtube.com/shorts/xyz987",
                "platform": "youtube",
            },
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-789"},
        )

        assert response.status_code == 201

    def test_add_reel_board_not_found(self, client: TestClient) -> None:
        """Test error when board doesn't exist."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceNotFound()
        )
        response = client.post(
            "/api/v1/boards/nonexistent/reels",
            json={
                "url": "https://www.instagram.com/reel/abc123/",
                "platform": "instagram",
            },
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-123"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "Board not found" in response.json()["detail"]

    def test_add_reel_user_not_member(self, client: TestClient) -> None:
        """Test error when user is not a member of the board."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceNotMember()
        )
        response = client.post(
            "/api/v1/boards/board-123/reels",
            json={
                "url": "https://www.instagram.com/reel/abc123/",
                "platform": "instagram",
            },
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-999"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    def test_add_duplicate_reel(self, client: TestClient) -> None:
        """Test error when reel already exists in board."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceDuplicate()
        )
        response = client.post(
            "/api/v1/boards/board-123/reels",
            json={
                "url": "https://www.instagram.com/reel/abc123/",
                "platform": "instagram",
            },
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-123"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_add_reel_missing_member_id(self, client: TestClient) -> None:
        """Test error when member_id header is missing."""
        response = client.post(
            "/api/v1/boards/board-123/reels",
            json={
                "url": "https://www.instagram.com/reel/abc123/",
                "platform": "instagram",
            },
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 400

    def test_add_reel_invalid_platform(self, client: TestClient) -> None:
        """Test error with invalid platform."""
        response = client.post(
            "/api/v1/boards/board-123/reels",
            json={
                "url": "https://www.instagram.com/reel/abc123/",
                "platform": "invalid_platform",
            },
            headers={"Authorization": "Bearer access-token", "X-Member-ID": "user-123"},
        )

        assert response.status_code == 422


# Tests for DELETE /boards/{board_id}/reels/{reel_id}
class TestDeleteReelFromBoard:
    def test_delete_reel_success(
        self,
        client: TestClient,
        stub_boards_service: StubBoardsService,
    ) -> None:
        """Test successfully deleting a reel from a board."""
        response = client.delete(
            "/api/v1/boards/board-123/reels/reel-1",
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Reel successfully deleted from board."

        # Verify the service was called correctly
        assert len(stub_boards_service.delete_reel_calls) == 1
        board_id, reel_id = stub_boards_service.delete_reel_calls[0]
        assert board_id == "board-123"
        assert reel_id == "reel-1"

    def test_delete_nonexistent_reel(self, client: TestClient) -> None:
        """Test error when reel doesn't exist."""
        from fastapi import HTTPException, status

        def failing_delete(*args, **kwargs):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reel not found in this board.",
            )

        service = StubBoardsService()
        service.delete_reel_from_board = failing_delete
        app.dependency_overrides[get_boards_service] = lambda: service

        response = client.delete(
            "/api/v1/boards/board-123/reels/nonexistent",
            headers={"Authorization": "Bearer access-token", "x-member-id": "user-123"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404

    def test_delete_reel_missing_member_id(self, client: TestClient) -> None:
        """Test error when member_id header is missing."""
        response = client.delete(
            "/api/v1/boards/board-123/reels/reel-1",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 400

    def test_delete_reel_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.delete(
            "/api/v1/boards/board-123/reels/reel-1",
            headers={"X-Member-ID": "user-123"},
        )

        assert response.status_code == 401
