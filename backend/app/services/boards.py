import httpx
from fastapi import HTTPException, status

from app.config import Settings
from app.schemas.boards import ReelCreateRequest, ReelResponse, ReelsListResponse


class BoardsService:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings
        self._supabase_url = str(settings.supabase_url).rstrip("/")
        self._headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
        }

    async def add_reel_to_board(
        self,
        board_id: str,
        member_id: str,
        payload: ReelCreateRequest,
    ) -> ReelResponse:
        """Add a reel to a board."""
        # Check if board exists
        await self._verify_board_exists(board_id)

        # Check if member belongs to board
        await self._verify_member_in_board(board_id, member_id)

        # Insert reel
        response = await self._http_client.post(
            f"{self._supabase_url}/rest/v1/reels",
            json={
                "board_id": board_id,
                "added_by": member_id,
                "url": payload.url,
                "platform": payload.platform,
            },
            headers=self._headers,
        )

        if response.status_code == status.HTTP_409_CONFLICT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This reel already exists in this board.",
            )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not add reel to board.",
            )

        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return ReelResponse(**data[0])

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not parse reel response.",
        )

    async def list_reels_in_board(
        self, board_id: str, limit: int = 100, offset: int = 0
    ) -> ReelsListResponse:
        """List all reels in a board."""
        # Check if board exists
        await self._verify_board_exists(board_id)

        # Fetch reels
        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/reels",
            params={
                "board_id": f"eq.{board_id}",
                "order": "created_at.desc",
                "limit": limit,
                "offset": offset,
            },
            headers=self._headers,
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch reels.",
            )

        reels_data = response.json()
        reels = [ReelResponse(**reel) for reel in reels_data]

        # Get total count
        count_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/reels",
            params={
                "board_id": f"eq.{board_id}",
                "select": "id",
            },
            headers={**self._headers, "Prefer": "count=exact"},
        )

        total = 0
        if count_response.status_code == 200:
            count_header = count_response.headers.get("content-range", "0/0")
            try:
                total = int(count_header.split("/")[1])
            except (IndexError, ValueError):
                total = len(reels)

        return ReelsListResponse(reels=reels, total=total, board_id=board_id)

    async def delete_reel_from_board(self, board_id: str, reel_id: str) -> dict:
        """Delete a reel from a board."""
        # Check if board exists
        await self._verify_board_exists(board_id)

        # Check if reel belongs to board
        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/reels",
            params={
                "id": f"eq.{reel_id}",
                "board_id": f"eq.{board_id}",
            },
            headers=self._headers,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch reel.",
            )

        data = response.json()
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reel not found in this board.",
            )

        # Delete reel
        delete_response = await self._http_client.delete(
            f"{self._supabase_url}/rest/v1/reels",
            params={
                "id": f"eq.{reel_id}",
                "board_id": f"eq.{board_id}",
            },
            headers=self._headers,
        )

        if delete_response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not delete reel.",
            )

        return {
            "success": True,
            "message": "Reel successfully deleted from board.",
        }

    async def _verify_board_exists(self, board_id: str) -> None:
        """Verify that a board exists."""
        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/boards",
            params={"id": f"eq.{board_id}"},
            headers=self._headers,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not verify board.",
            )

        data = response.json()
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found.",
            )

    async def _verify_member_in_board(self, board_id: str, member_id: str) -> None:
        """Verify that a member belongs to a board."""
        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/members",
            params={
                "board_id": f"eq.{board_id}",
                "id": f"eq.{member_id}",
            },
            headers=self._headers,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not verify membership.",
            )

        data = response.json()
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this board.",
            )
