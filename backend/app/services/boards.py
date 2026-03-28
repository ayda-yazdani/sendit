import httpx
from fastapi import HTTPException, status
import uuid
import string
import random

from app.config import Settings
from app.schemas.boards import (
    ReelCreateRequest,
    ReelResponse,
    ReelsListResponse,
    BoardCreateRequest,
    BoardResponse,
    BoardListResponse,
    MemberCreateRequest,
    MemberResponse,
    MembersListResponse,
    MemberUpdateRequest,
    BoardJoinRequest,
)


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

    # ===== Board Management Methods =====

    async def create_board(
        self, payload: BoardCreateRequest, user_device_id: str
    ) -> BoardResponse:
        """Create a new board and add the creator as first member."""
        board_id = str(uuid.uuid4())
        join_code = self._generate_join_code()

        # Create board
        board_response = await self._http_client.post(
            f"{self._supabase_url}/rest/v1/boards",
            json={
                "id": board_id,
                "name": payload.name,
                "join_code": join_code,
            },
            headers=self._headers,
        )

        if board_response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not create board.",
            )

        # Add creator as first member
        member_response = await self._http_client.post(
            f"{self._supabase_url}/rest/v1/members",
            json={
                "board_id": board_id,
                "display_name": payload.display_name,
                "device_id": user_device_id,
            },
            headers=self._headers,
        )

        if member_response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not add creator to board.",
            )

        return BoardResponse(
            id=board_id,
            name=payload.name,
            join_code=join_code,
            member_count=1,
        )

    async def list_user_boards(self, user_device_id: str) -> BoardListResponse:
        """List all boards the user is a member of."""
        # Get all members for this device
        members_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/members",
            params={
                "device_id": f"eq.{user_device_id}",
                "select": "board_id",
            },
            headers=self._headers,
        )

        if members_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch user boards.",
            )

        members_data = members_response.json()
        board_ids = [m["board_id"] for m in members_data if "board_id" in m]

        if not board_ids:
            return BoardListResponse(boards=[], total=0)

        # Fetch board details for each board_id
        boards = []
        for board_id in board_ids:
            board_response = await self._http_client.get(
                f"{self._supabase_url}/rest/v1/boards",
                params={"id": f"eq.{board_id}"},
                headers=self._headers,
            )

            if board_response.status_code == 200:
                board_data = board_response.json()
                if board_data:
                    # Get member count
                    count_response = await self._http_client.get(
                        f"{self._supabase_url}/rest/v1/members",
                        params={"board_id": f"eq.{board_id}"},
                        headers={**self._headers, "Prefer": "count=exact"},
                    )
                    member_count = 1
                    if count_response.status_code == 200:
                        count_header = count_response.headers.get("content-range", "0/0")
                        try:
                            member_count = int(count_header.split("/")[1])
                        except (IndexError, ValueError):
                            pass

                    board = board_data[0]
                    boards.append(
                        BoardResponse(
                            id=board["id"],
                            name=board["name"],
                            join_code=board["join_code"],
                            member_count=member_count,
                            created_at=board.get("created_at"),
                        )
                    )

        return BoardListResponse(boards=boards, total=len(boards))

    async def get_board(self, board_id: str) -> BoardResponse:
        """Get board details with member count."""
        board_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/boards",
            params={"id": f"eq.{board_id}"},
            headers=self._headers,
        )

        if board_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch board.",
            )

        board_data = board_response.json()
        if not board_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found.",
            )

        board = board_data[0]

        # Get member count
        count_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/members",
            params={"board_id": f"eq.{board_id}"},
            headers={**self._headers, "Prefer": "count=exact"},
        )

        member_count = 1
        if count_response.status_code == 200:
            count_header = count_response.headers.get("content-range", "0/0")
            try:
                member_count = int(count_header.split("/")[1])
            except (IndexError, ValueError):
                pass

        return BoardResponse(
            id=board["id"],
            name=board["name"],
            join_code=board["join_code"],
            member_count=member_count,
            created_at=board.get("created_at"),
        )

    async def join_board(
        self, payload: BoardJoinRequest, user_device_id: str
    ) -> BoardResponse:
        """Join a board using the join code."""
        # Verify board exists and get board_id from join_code
        board_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/boards",
            params={"join_code": f"eq.{payload.join_code}"},
            headers=self._headers,
        )

        if board_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not verify board.",
            )

        board_data = board_response.json()
        if not board_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid join code.",
            )

        board = board_data[0]
        board_id = board["id"]

        # Check if user is already a member
        member_check = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/members",
            params={
                "board_id": f"eq.{board_id}",
                "device_id": f"eq.{user_device_id}",
            },
            headers=self._headers,
        )

        if member_check.status_code == 200:
            existing = member_check.json()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You are already a member of this board.",
                )

        # Add user as member
        member_response = await self._http_client.post(
            f"{self._supabase_url}/rest/v1/members",
            json={
                "board_id": board_id,
                "display_name": payload.display_name,
                "device_id": user_device_id,
            },
            headers=self._headers,
        )

        if member_response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not join board.",
            )

        return await self.get_board(board_id)

    async def delete_board(self, board_id: str) -> dict:
        """Delete a board (cascades to members and reels)."""
        await self._verify_board_exists(board_id)

        # Delete board (should cascade delete members and reels due to FK constraints)
        response = await self._http_client.delete(
            f"{self._supabase_url}/rest/v1/boards",
            params={"id": f"eq.{board_id}"},
            headers=self._headers,
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not delete board.",
            )

        return {"success": True, "message": "Board successfully deleted."}

    # ===== Member Management Methods =====

    async def list_board_members(
        self, board_id: str, limit: int = 100, offset: int = 0
    ) -> MembersListResponse:
        """List all members in a board."""
        await self._verify_board_exists(board_id)

        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/members",
            params={
                "board_id": f"eq.{board_id}",
                "order": "created_at.asc",
                "limit": limit,
                "offset": offset,
            },
            headers=self._headers,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch members.",
            )

        members_data = response.json()
        members = [MemberResponse(**member) for member in members_data]

        # Get total count
        count_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/members",
            params={"board_id": f"eq.{board_id}"},
            headers={**self._headers, "Prefer": "count=exact"},
        )

        total = len(members)
        if count_response.status_code == 200:
            count_header = count_response.headers.get("content-range", "0/0")
            try:
                total = int(count_header.split("/")[1])
            except (IndexError, ValueError):
                pass

        return MembersListResponse(members=members, total=total, board_id=board_id)

    async def update_member_profile(
        self, board_id: str, member_id: str, payload: MemberUpdateRequest
    ) -> MemberResponse:
        """Update a member's profile (display_name, avatar_url)."""
        await self._verify_board_exists(board_id)
        await self._verify_member_in_board(board_id, member_id)

        update_data = {}
        if payload.display_name is not None:
            update_data["display_name"] = payload.display_name
        if payload.avatar_url is not None:
            update_data["avatar_url"] = payload.avatar_url

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            )

        response = await self._http_client.patch(
            f"{self._supabase_url}/rest/v1/members",
            params={"id": f"eq.{member_id}"},
            json=update_data,
            headers=self._headers,
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not update member profile.",
            )

        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return MemberResponse(**data[0])

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not parse member response.",
        )

    async def delete_member_from_board(
        self, board_id: str, member_id: str
    ) -> dict:
        """Remove a member from a board."""
        await self._verify_board_exists(board_id)
        await self._verify_member_in_board(board_id, member_id)

        response = await self._http_client.delete(
            f"{self._supabase_url}/rest/v1/members",
            params={
                "id": f"eq.{member_id}",
                "board_id": f"eq.{board_id}",
            },
            headers=self._headers,
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not remove member from board.",
            )

        return {"success": True, "message": "Member successfully removed from board."}

    def _generate_join_code(self) -> str:
        """Generate a 6-character alphanumeric join code."""
        characters = string.ascii_uppercase + string.digits
        return "".join(random.choice(characters) for _ in range(6))
