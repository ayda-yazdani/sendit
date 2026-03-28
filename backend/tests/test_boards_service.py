import json
from datetime import datetime
from typing import Any

import httpx
import pytest
from fastapi import HTTPException, status

from app.config import Settings
from app.schemas.boards import ReelCreateRequest
from app.services.boards import BoardsService


class MockAsyncClient:
    """Mock httpx.AsyncClient for testing."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.responses: list[httpx.Response] = []
        self.response_queue: list[httpx.Response] = []

    def add_response(self, response: httpx.Response) -> None:
        """Queue a response for the next request."""
        self.response_queue.append(response)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Mock GET request."""
        self.requests.append({"method": "GET", "url": url, "kwargs": kwargs})
        if self.response_queue:
            return self.response_queue.pop(0)
        return httpx.Response(200, json=[])

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Mock POST request."""
        self.requests.append({"method": "POST", "url": url, "kwargs": kwargs})
        if self.response_queue:
            return self.response_queue.pop(0)
        return httpx.Response(200, json={})

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Mock DELETE request."""
        self.requests.append({"method": "DELETE", "url": url, "kwargs": kwargs})
        if self.response_queue:
            return self.response_queue.pop(0)
        return httpx.Response(204)


@pytest.fixture
def mock_client() -> MockAsyncClient:
    return MockAsyncClient()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        supabase_url="https://example.supabase.co",
        supabase_key="test-key",
    )


@pytest.fixture
def boards_service(mock_client: MockAsyncClient, settings: Settings) -> BoardsService:
    return BoardsService(http_client=mock_client, settings=settings)


class TestAddReelToBoard:
    @pytest.mark.asyncio
    async def test_add_reel_success(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test successfully adding a reel to a board."""
        # Mock board verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "board-123", "name": "Test Board"}],
            )
        )

        # Mock member verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[
                    {
                        "id": "user-123",
                        "board_id": "board-123",
                        "display_name": "Test User",
                    }
                ],
            )
        )

        # Mock reel insert
        mock_client.add_response(
            httpx.Response(
                201,
                json=[
                    {
                        "id": "reel-123",
                        "board_id": "board-123",
                        "added_by": "user-123",
                        "url": "https://www.instagram.com/reel/abc123/",
                        "platform": "instagram",
                        "classification": "real_event",
                        "extraction_data": {"type": "real_event"},
                        "created_at": "2026-03-28T12:00:00Z",
                    }
                ],
            )
        )

        payload = ReelCreateRequest(
            url="https://www.instagram.com/reel/abc123/",
            platform="instagram",
        )

        result = await boards_service.add_reel_to_board(
            board_id="board-123",
            member_id="user-123",
            payload=payload,
        )

        assert result.id == "reel-123"
        assert result.platform == "instagram"
        assert result.url == "https://www.instagram.com/reel/abc123/"

    @pytest.mark.asyncio
    async def test_add_reel_board_not_found(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test error when board doesn't exist."""
        # Mock board verification returning empty
        mock_client.add_response(httpx.Response(200, json=[]))

        payload = ReelCreateRequest(
            url="https://www.instagram.com/reel/abc123/",
            platform="instagram",
        )

        with pytest.raises(HTTPException) as exc_info:
            await boards_service.add_reel_to_board(
                board_id="nonexistent",
                member_id="user-123",
                payload=payload,
            )

        assert exc_info.value.status_code == 404
        assert "Board not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_add_reel_user_not_member(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test error when user is not a member of the board."""
        # Mock board exists
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "board-123", "name": "Test Board"}],
            )
        )

        # Mock member verification returning empty
        mock_client.add_response(httpx.Response(200, json=[]))

        payload = ReelCreateRequest(
            url="https://www.instagram.com/reel/abc123/",
            platform="instagram",
        )

        with pytest.raises(HTTPException) as exc_info:
            await boards_service.add_reel_to_board(
                board_id="board-123",
                member_id="user-999",
                payload=payload,
            )

        assert exc_info.value.status_code == 403
        assert "not a member" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_add_duplicate_reel(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test error when reel already exists (conflict)."""
        # Mock board verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "board-123", "name": "Test Board"}],
            )
        )

        # Mock member verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "user-123", "board_id": "board-123"}],
            )
        )

        # Mock reel insert returning 409 conflict
        mock_client.add_response(httpx.Response(409, json={"error": "Conflict"}))

        payload = ReelCreateRequest(
            url="https://www.instagram.com/reel/abc123/",
            platform="instagram",
        )

        with pytest.raises(HTTPException) as exc_info:
            await boards_service.add_reel_to_board(
                board_id="board-123",
                member_id="user-123",
                payload=payload,
            )

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail


class TestListReelsInBoard:
    @pytest.mark.asyncio
    async def test_list_reels_success(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test successfully listing reels in a board."""
        # Mock board verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "board-123", "name": "Test Board"}],
            )
        )

        # Mock reels fetch
        mock_client.add_response(
            httpx.Response(
                200,
                json=[
                    {
                        "id": "reel-1",
                        "board_id": "board-123",
                        "added_by": "user-123",
                        "url": "https://www.instagram.com/reel/abc123/",
                        "platform": "instagram",
                        "classification": "real_event",
                        "extraction_data": {"type": "real_event"},
                        "created_at": "2026-03-28T10:00:00Z",
                    },
                    {
                        "id": "reel-2",
                        "board_id": "board-123",
                        "added_by": "user-456",
                        "url": "https://www.tiktok.com/@creator/video/9876543210",
                        "platform": "tiktok",
                        "classification": "vibe_inspiration",
                        "extraction_data": {"type": "vibe_inspiration"},
                        "created_at": "2026-03-28T11:00:00Z",
                    },
                ],
                headers={"content-range": "0-1/2"},
            )
        )

        # Mock count fetch
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "reel-1"}, {"id": "reel-2"}],
                headers={"content-range": "0-1/2"},
            )
        )

        result = await boards_service.list_reels_in_board(
            board_id="board-123",
            limit=100,
            offset=0,
        )

        assert result.board_id == "board-123"
        assert len(result.reels) == 2
        assert result.total == 2
        assert result.reels[0].id == "reel-1"
        assert result.reels[0].platform == "instagram"
        assert result.reels[1].id == "reel-2"
        assert result.reels[1].platform == "tiktok"

    @pytest.mark.asyncio
    async def test_list_reels_with_pagination(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test listing reels with limit and offset."""
        # Mock board verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "board-123", "name": "Test Board"}],
            )
        )

        # Mock reels fetch with pagination
        mock_client.add_response(
            httpx.Response(
                200,
                json=[
                    {
                        "id": "reel-1",
                        "board_id": "board-123",
                        "added_by": "user-123",
                        "url": "https://www.instagram.com/reel/abc123/",
                        "platform": "instagram",
                        "classification": None,
                        "extraction_data": None,
                        "created_at": "2026-03-28T10:00:00Z",
                    },
                ],
                headers={"content-range": "10-10/25"},
            )
        )

        # Mock count fetch
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "reel-1"}],
                headers={"content-range": "10-10/25"},
            )
        )

        result = await boards_service.list_reels_in_board(
            board_id="board-123",
            limit=10,
            offset=10,
        )

        assert len(result.reels) == 1
        assert result.total == 25

    @pytest.mark.asyncio
    async def test_list_reels_board_not_found(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test error when board doesn't exist."""
        # Mock board verification returning empty
        mock_client.add_response(httpx.Response(200, json=[]))

        with pytest.raises(HTTPException) as exc_info:
            await boards_service.list_reels_in_board(board_id="nonexistent")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_empty_reels(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test listing reels when board has none."""
        # Mock board verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "board-123", "name": "Test Board"}],
            )
        )

        # Mock reels fetch returning empty
        mock_client.add_response(
            httpx.Response(
                200,
                json=[],
                headers={"content-range": "0-0/0"},
            )
        )

        # Mock count fetch
        mock_client.add_response(
            httpx.Response(
                200,
                json=[],
                headers={"content-range": "0-0/0"},
            )
        )

        result = await boards_service.list_reels_in_board(board_id="board-123")

        assert len(result.reels) == 0
        assert result.total == 0


class TestDeleteReelFromBoard:
    @pytest.mark.asyncio
    async def test_delete_reel_success(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test successfully deleting a reel from a board."""
        # Mock board verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "board-123", "name": "Test Board"}],
            )
        )

        # Mock reel verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[
                    {
                        "id": "reel-1",
                        "board_id": "board-123",
                        "url": "https://www.instagram.com/reel/abc123/",
                    }
                ],
            )
        )

        # Mock delete
        mock_client.add_response(httpx.Response(204))

        result = await boards_service.delete_reel_from_board(
            board_id="board-123",
            reel_id="reel-1",
        )

        assert result["success"] is True
        assert "deleted" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_reel_board_not_found(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test error when board doesn't exist."""
        # Mock board verification returning empty
        mock_client.add_response(httpx.Response(200, json=[]))

        with pytest.raises(HTTPException) as exc_info:
            await boards_service.delete_reel_from_board(
                board_id="nonexistent",
                reel_id="reel-1",
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_reel(
        self,
        boards_service: BoardsService,
        mock_client: MockAsyncClient,
    ) -> None:
        """Test error when reel doesn't exist in board."""
        # Mock board verification
        mock_client.add_response(
            httpx.Response(
                200,
                json=[{"id": "board-123", "name": "Test Board"}],
            )
        )

        # Mock reel verification returning empty
        mock_client.add_response(httpx.Response(200, json=[]))

        with pytest.raises(HTTPException) as exc_info:
            await boards_service.delete_reel_from_board(
                board_id="board-123",
                reel_id="nonexistent",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail
