from collections.abc import Generator
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_boards_service, get_supabase_auth_service
from app.main import app
from app.schemas.auth import SupabaseSession, SupabaseUser, UserResponse
from app.schemas.boards import (
    BoardCreateRequest,
    BoardResponse,
    BoardListResponse,
    BoardJoinRequest,
    MemberCreateRequest,
    MemberResponse,
    MembersListResponse,
    MemberUpdateRequest,
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


class StubBoardsService:
    """Mock boards service for testing."""

    def __init__(self) -> None:
        self.create_board_calls: list[tuple[BoardCreateRequest, str]] = []
        self.list_user_boards_calls: list[str] = []
        self.get_board_calls: list[str] = []
        self.join_board_calls: list[tuple[BoardJoinRequest, str]] = []
        self.delete_board_calls: list[str] = []
        self.list_members_calls: list[tuple[str, int, int]] = []
        self.update_member_calls: list[tuple[str, str, MemberUpdateRequest]] = []
        self.delete_member_calls: list[tuple[str, str]] = []

    async def create_board(
        self, payload: BoardCreateRequest, user_device_id: str
    ) -> BoardResponse:
        self.create_board_calls.append((payload, user_device_id))
        return BoardResponse(
            id="board-123",
            name=payload.name,
            join_code="ABC123",
            member_count=1,
            created_at=datetime.fromisoformat("2026-03-28T12:00:00"),
        )

    async def list_user_boards(self, user_device_id: str) -> BoardListResponse:
        self.list_user_boards_calls.append(user_device_id)
        return BoardListResponse(
            boards=[
                BoardResponse(
                    id="board-1",
                    name="Summer Friends",
                    join_code="ABC123",
                    member_count=3,
                    created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
                ),
                BoardResponse(
                    id="board-2",
                    name="Work Gang",
                    join_code="XYZ789",
                    member_count=5,
                    created_at=datetime.fromisoformat("2026-03-27T15:00:00"),
                ),
            ],
            total=2,
        )

    async def get_board(self, board_id: str) -> BoardResponse:
        self.get_board_calls.append(board_id)
        return BoardResponse(
            id=board_id,
            name="Summer Friends",
            join_code="ABC123",
            member_count=3,
            created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
        )

    async def join_board(
        self, payload: BoardJoinRequest, user_device_id: str
    ) -> BoardResponse:
        self.join_board_calls.append((payload, user_device_id))
        return BoardResponse(
            id="board-999",
            name="Mystery Board",
            join_code=payload.join_code,
            member_count=4,
            created_at=datetime.fromisoformat("2026-03-25T08:00:00"),
        )

    async def delete_board(self, board_id: str) -> dict:
        self.delete_board_calls.append(board_id)
        return {"success": True, "message": "Board successfully deleted."}

    async def list_board_members(
        self, board_id: str, limit: int = 100, offset: int = 0
    ) -> MembersListResponse:
        self.list_members_calls.append((board_id, limit, offset))
        return MembersListResponse(
            members=[
                MemberResponse(
                    id="member-1",
                    board_id=board_id,
                    display_name="Alice",
                    device_id="device-1",
                    google_id=None,
                    avatar_url="https://example.com/alice.jpg",
                    created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
                ),
                MemberResponse(
                    id="member-2",
                    board_id=board_id,
                    display_name="Bob",
                    device_id="device-2",
                    google_id=None,
                    avatar_url=None,
                    created_at=datetime.fromisoformat("2026-03-28T11:00:00"),
                ),
                MemberResponse(
                    id="member-3",
                    board_id=board_id,
                    display_name="Charlie",
                    device_id="device-3",
                    google_id="charlie-google-id",
                    avatar_url="https://example.com/charlie.jpg",
                    created_at=datetime.fromisoformat("2026-03-28T12:00:00"),
                ),
            ],
            total=3,
            board_id=board_id,
        )

    async def update_member_profile(
        self, board_id: str, member_id: str, payload: MemberUpdateRequest
    ) -> MemberResponse:
        self.update_member_calls.append((board_id, member_id, payload))
        return MemberResponse(
            id=member_id,
            board_id=board_id,
            display_name=payload.display_name or "Updated Name",
            device_id="device-123",
            google_id=None,
            avatar_url=payload.avatar_url or "https://example.com/avatar.jpg",
            created_at=datetime.fromisoformat("2026-03-28T12:00:00"),
        )

    async def delete_member_from_board(self, board_id: str, member_id: str) -> dict:
        self.delete_member_calls.append((board_id, member_id))
        return {"success": True, "message": "Member successfully removed from board."}


class StubBoardsServiceBoardNotFound(StubBoardsService):
    async def get_board(self, board_id: str) -> BoardResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found.",
        )


class StubBoardsServiceInvalidCode(StubBoardsService):
    async def join_board(
        self, payload: BoardJoinRequest, user_device_id: str
    ) -> BoardResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid join code.",
        )


class StubBoardsServiceEmptyBoardsList(StubBoardsService):
    async def list_user_boards(self, user_device_id: str) -> BoardListResponse:
        return BoardListResponse(boards=[], total=0)


class StubBoardsServiceAlreadyMember(StubBoardsService):
    async def join_board(
        self, payload: BoardJoinRequest, user_device_id: str
    ) -> BoardResponse:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this board.",
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


# ===== PHASE 1: BOARD MANAGEMENT TESTS =====


class TestCreateBoard:
    def test_create_board_success(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test successfully creating a new board."""
        response = client.post(
            "/api/v1/boards",
            json={"name": "Summer Trip", "display_name": "Alice"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "board-123"
        assert data["name"] == "Summer Trip"
        assert data["join_code"] == "ABC123"
        assert data["member_count"] == 1

        # Verify service was called
        assert len(stub_boards_service.create_board_calls) == 1
        payload, device_id = stub_boards_service.create_board_calls[0]
        assert payload.name == "Summer Trip"
        assert payload.display_name == "Alice"
        assert device_id == "device-123"

    def test_create_board_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.post(
            "/api/v1/boards",
            json={"name": "Summer Trip", "display_name": "Alice"},
        )

        assert response.status_code == 401

    def test_create_board_missing_name(self, client: TestClient) -> None:
        """Test error when name is missing."""
        response = client.post(
            "/api/v1/boards",
            json={"display_name": "Alice"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 422


class TestListUserBoards:
    def test_list_user_boards_success(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test successfully listing user's boards."""
        response = client.get(
            "/api/v1/boards",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["boards"]) == 2
        assert data["total"] == 2
        assert data["boards"][0]["name"] == "Summer Friends"
        assert data["boards"][0]["member_count"] == 3
        assert data["boards"][1]["name"] == "Work Gang"
        assert data["boards"][1]["member_count"] == 5

        # Verify service was called
        assert len(stub_boards_service.list_user_boards_calls) == 1

    def test_list_user_boards_empty(self, client: TestClient) -> None:
        """Test listing boards when user has none."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceEmptyBoardsList()
        )
        response = client.get(
            "/api/v1/boards",
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data["boards"]) == 0
        assert data["total"] == 0

    def test_list_user_boards_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.get("/api/v1/boards")

        assert response.status_code == 401


class TestGetBoard:
    def test_get_board_success(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test successfully getting board details."""
        response = client.get(
            "/api/v1/boards/board-123",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "board-123"
        assert data["name"] == "Summer Friends"
        assert data["member_count"] == 3

        # Verify service was called
        assert len(stub_boards_service.get_board_calls) == 1
        assert stub_boards_service.get_board_calls[0] == "board-123"

    def test_get_nonexistent_board(self, client: TestClient) -> None:
        """Test error when board doesn't exist."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceBoardNotFound()
        )
        response = client.get(
            "/api/v1/boards/nonexistent",
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "Board not found" in response.json()["detail"]

    def test_get_board_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.get("/api/v1/boards/board-123")

        assert response.status_code == 401


class TestJoinBoard:
    def test_join_board_success(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test successfully joining a board."""
        response = client.post(
            "/api/v1/boards/join",
            json={"join_code": "ABC123", "display_name": "David"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "board-999"
        assert data["name"] == "Mystery Board"
        assert data["member_count"] == 4

        # Verify service was called
        assert len(stub_boards_service.join_board_calls) == 1
        payload, device_id = stub_boards_service.join_board_calls[0]
        assert payload.join_code == "ABC123"
        assert payload.display_name == "David"
        assert device_id == "device-123"

    def test_join_board_invalid_code(self, client: TestClient) -> None:
        """Test error with invalid join code."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceInvalidCode()
        )
        response = client.post(
            "/api/v1/boards/join",
            json={"join_code": "INVALID", "display_name": "David"},
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "Invalid join code" in response.json()["detail"]

    def test_join_board_already_member(self, client: TestClient) -> None:
        """Test error when user is already a member."""
        app.dependency_overrides[get_boards_service] = (
            lambda: StubBoardsServiceAlreadyMember()
        )
        response = client.post(
            "/api/v1/boards/join",
            json={"join_code": "ABC123", "display_name": "David"},
            headers={"Authorization": "Bearer access-token"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 409
        assert "already a member" in response.json()["detail"]

    def test_join_board_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.post(
            "/api/v1/boards/join",
            json={"join_code": "ABC123", "display_name": "David"},
        )

        assert response.status_code == 401


class TestDeleteBoard:
    def test_delete_board_success(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test successfully deleting a board."""
        response = client.delete(
            "/api/v1/boards/board-123",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify service was called
        assert len(stub_boards_service.delete_board_calls) == 1
        assert stub_boards_service.delete_board_calls[0] == "board-123"

    def test_delete_board_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.delete("/api/v1/boards/board-123")

        assert response.status_code == 401


# ===== PHASE 2: MEMBER MANAGEMENT TESTS =====


class TestListBoardMembers:
    def test_list_board_members_success(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test successfully listing board members."""
        response = client.get(
            "/api/v1/boards/board-123/members",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["members"]) == 3
        assert data["total"] == 3
        assert data["board_id"] == "board-123"
        assert data["members"][0]["display_name"] == "Alice"
        assert data["members"][1]["display_name"] == "Bob"
        assert data["members"][2]["display_name"] == "Charlie"

        # Verify service was called
        assert len(stub_boards_service.list_members_calls) == 1

    def test_list_board_members_with_pagination(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test listing members with pagination."""
        response = client.get(
            "/api/v1/boards/board-123/members?limit=10&offset=5",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        assert len(stub_boards_service.list_members_calls) == 1
        board_id, limit, offset = stub_boards_service.list_members_calls[0]
        assert board_id == "board-123"
        assert limit == 10
        assert offset == 5

    def test_list_board_members_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.get("/api/v1/boards/board-123/members")

        assert response.status_code == 401


class TestUpdateMemberProfile:
    def test_update_member_display_name(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test updating member's display name."""
        response = client.patch(
            "/api/v1/boards/board-123/members/member-1",
            json={"display_name": "Alice Smith"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "member-1"
        assert data["display_name"] == "Alice Smith"

        # Verify service was called
        assert len(stub_boards_service.update_member_calls) == 1

    def test_update_member_avatar(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test updating member's avatar."""
        response = client.patch(
            "/api/v1/boards/board-123/members/member-1",
            json={"avatar_url": "https://example.com/new-avatar.jpg"},
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] == "https://example.com/new-avatar.jpg"

    def test_update_member_both_fields(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test updating both display name and avatar."""
        response = client.patch(
            "/api/v1/boards/board-123/members/member-1",
            json={
                "display_name": "Alice Smith",
                "avatar_url": "https://example.com/new-avatar.jpg",
            },
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200

    def test_update_member_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.patch(
            "/api/v1/boards/board-123/members/member-1",
            json={"display_name": "New Name"},
        )

        assert response.status_code == 401


class TestDeleteMember:
    def test_delete_member_success(
        self, client: TestClient, stub_boards_service: StubBoardsService
    ) -> None:
        """Test successfully removing a member from board."""
        response = client.delete(
            "/api/v1/boards/board-123/members/member-1",
            headers={"Authorization": "Bearer access-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify service was called
        assert len(stub_boards_service.delete_member_calls) == 1
        board_id, member_id = stub_boards_service.delete_member_calls[0]
        assert board_id == "board-123"
        assert member_id == "member-1"

    def test_delete_member_missing_auth(self, client: TestClient) -> None:
        """Test error when authorization is missing."""
        response = client.delete("/api/v1/boards/board-123/members/member-1")

        assert response.status_code == 401
