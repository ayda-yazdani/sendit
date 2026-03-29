import httpx
from fastapi import HTTPException, status
import uuid
import string
import random
import json
from datetime import datetime

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
    TasteProfileResponse,
    TasteProfileSyncRequest,
    TasteProfileUpdateRequest,
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
            headers={**self._headers, "Prefer": "return=representation"},
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
            headers={**self._headers, "Prefer": "return=representation"},
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
            headers={**self._headers, "Prefer": "return=representation"},
        )

        if member_response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not add creator to board.",
            )

        board_data = board_response.json()
        board = board_data[0] if isinstance(board_data, list) and board_data else {}

        return BoardResponse(
            id=board.get("id", board_id),
            name=board.get("name", payload.name),
            join_code=board.get("join_code", join_code),
            member_count=1,
            created_at=board.get("created_at", datetime.utcnow().isoformat()),
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
            headers={**self._headers, "Prefer": "return=representation"},
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
            headers={**self._headers, "Prefer": "return=representation"},
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

    # ===== Taste Profile Methods =====

    async def get_taste_profile(self, board_id: str) -> TasteProfileResponse:
        """Fetch the taste profile for a board."""
        await self._verify_board_exists(board_id)

        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/taste_profiles",
            params={"board_id": f"eq.{board_id}"},
            headers=self._headers,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch taste profile.",
            )

        data = response.json()
        if not data or len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Taste profile not found for this board.",
            )

        return TasteProfileResponse(**data[0])

    async def sync_taste_profile(
        self, board_id: str, payload: TasteProfileSyncRequest
    ) -> TasteProfileResponse:
        """
        Generate or update the taste profile for a board.
        Analyzes all reels and generates aggregated profile data.
        """
        await self._verify_board_exists(board_id)

        # Fetch all reels for this board
        reels_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/reels",
            params={
                "board_id": f"eq.{board_id}",
                "limit": 1000,
            },
            headers=self._headers,
        )

        if reels_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch reels for profile generation.",
            )

        reels_data = reels_response.json()

        # Check if taste profile already exists
        profile_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/taste_profiles",
            params={"board_id": f"eq.{board_id}"},
            headers=self._headers,
        )

        existing_profile = None
        if profile_response.status_code == 200:
            data = profile_response.json()
            if data and len(data) > 0:
                existing_profile = data[0]

        # Aggregate data from reels
        activity_types = self._extract_activity_types(reels_data)
        aesthetic_register = self._extract_aesthetic_register(reels_data)
        food_preferences = self._extract_food_preferences(reels_data)
        location_patterns = self._extract_location_patterns(reels_data)
        price_range = self._extract_price_range(reels_data)
        vibe_tags = self._extract_vibe_tags(reels_data)
        identity_label = self._generate_identity_label(
            activity_types, aesthetic_register, location_patterns
        )

        profile_data = {
            "board_id": board_id,
            "activity_types": activity_types,
            "aesthetic_register": aesthetic_register,
            "food_preferences": food_preferences,
            "location_patterns": location_patterns,
            "price_range": price_range,
            "vibe_tags": vibe_tags,
            "identity_label": identity_label,
            "reel_count": len(reels_data),
            "updated_at": datetime.utcnow().isoformat(),
        }

        if existing_profile:
            # Update existing profile
            profile_data["id"] = existing_profile["id"]
            response = await self._http_client.patch(
                f"{self._supabase_url}/rest/v1/taste_profiles",
                params={"id": f"eq.{existing_profile['id']}"},
                json=profile_data,
                headers={**self._headers, "Prefer": "return=representation"},
            )
        else:
            # Create new profile
            profile_data["id"] = str(uuid.uuid4())
            profile_data["created_at"] = datetime.utcnow().isoformat()
            response = await self._http_client.post(
                f"{self._supabase_url}/rest/v1/taste_profiles",
                json=profile_data,
                headers={**self._headers, "Prefer": "return=representation"},
            )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not save taste profile.",
            )

        result_data = response.json()
        if isinstance(result_data, list) and len(result_data) > 0:
            return TasteProfileResponse(**result_data[0])

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not parse profile response.",
        )

    async def update_taste_profile(
        self, board_id: str, payload: TasteProfileUpdateRequest
    ) -> TasteProfileResponse:
        """Manually update specific fields in a taste profile."""
        await self._verify_board_exists(board_id)

        profile_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/taste_profiles",
            params={"board_id": f"eq.{board_id}"},
            headers=self._headers,
        )

        if profile_response.status_code != 200 or not profile_response.json():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Taste profile not found. Generate one first using /sync.",
            )

        existing_profile = profile_response.json()[0]

        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if payload.activity_types is not None:
            update_data["activity_types"] = payload.activity_types
        if payload.aesthetic_register is not None:
            update_data["aesthetic_register"] = payload.aesthetic_register
        if payload.food_preferences is not None:
            update_data["food_preferences"] = payload.food_preferences
        if payload.location_patterns is not None:
            update_data["location_patterns"] = payload.location_patterns
        if payload.price_range is not None:
            update_data["price_range"] = payload.price_range
        if payload.vibe_tags is not None:
            update_data["vibe_tags"] = payload.vibe_tags
        if payload.identity_label is not None:
            update_data["identity_label"] = payload.identity_label

        response = await self._http_client.patch(
            f"{self._supabase_url}/rest/v1/taste_profiles",
            params={"id": f"eq.{existing_profile['id']}"},
            json=update_data,
            headers={**self._headers, "Prefer": "return=representation"},
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not update taste profile.",
            )

        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return TasteProfileResponse(**data[0])

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not parse profile response.",
        )

    # ===== Helper Methods for Taste Profile Generation =====

    def _extract_activity_types(self, reels: list) -> list[str]:
        """Extract activity types from reel classifications."""
        activity_types = set()

        for reel in reels:
            classification = reel.get("classification")
            if classification == "real_event":
                activity_types.add("events")
            elif classification == "real_venue":
                activity_types.add("venues")
            elif classification == "recipe_food":
                activity_types.add("dining")
            elif classification == "vibe_inspiration":
                activity_types.add("inspiration")

        # Default if no reels yet
        if not activity_types:
            return []

        return sorted(list(activity_types))

    def _extract_aesthetic_register(self, reels: list) -> list[str]:
        """Extract aesthetic tags from extraction data."""
        aesthetics = set()

        for reel in reels:
            extraction_data = reel.get("extraction_data") or {}
            if isinstance(extraction_data, dict):
                vibe = extraction_data.get("vibe")
                if vibe and isinstance(vibe, str):
                    aesthetics.add(vibe.lower())

        return sorted(list(aesthetics))

    def _extract_food_preferences(self, reels: list) -> list[str]:
        """Extract food preferences from reels classified as recipes/food."""
        food_prefs = set()

        for reel in reels:
            if reel.get("classification") == "recipe_food":
                extraction_data = reel.get("extraction_data") or {}
                if isinstance(extraction_data, dict):
                    cuisine = extraction_data.get("cuisine")
                    if cuisine and isinstance(cuisine, str):
                        food_prefs.add(cuisine)

        return sorted(list(food_prefs))

    def _extract_location_patterns(self, reels: list) -> list[str]:
        """Extract location patterns from venue and event data."""
        locations = set()

        for reel in reels:
            extraction_data = reel.get("extraction_data") or {}
            if isinstance(extraction_data, dict):
                location = extraction_data.get("location")
                if location and isinstance(location, str):
                    locations.add(location.lower())

        return sorted(list(locations))

    def _extract_price_range(self, reels: list) -> str | None:
        """Estimate price range from average prices in extraction data."""
        prices = []

        for reel in reels:
            extraction_data = reel.get("extraction_data") or {}
            if isinstance(extraction_data, dict):
                price = extraction_data.get("price_per_person")
                if isinstance(price, (int, float)):
                    prices.append(price)

        if not prices:
            return None

        avg_price = sum(prices) / len(prices)
        if avg_price < 10:
            return "£0-10"
        elif avg_price < 20:
            return "£10-20"
        elif avg_price < 30:
            return "£20-30"
        elif avg_price < 50:
            return "£30-50"
        else:
            return "£50+"

    def _extract_vibe_tags(self, reels: list) -> list[str]:
        """Extract vibe tags from reel titles and metadata."""
        vibes = set()

        vibe_keywords = {
            "underground": ["underground", "indie", "basement"],
            "upscale": ["upscale", "fine dining", "luxury", "exclusive"],
            "casual": ["casual", "chill", "relaxed"],
            "high energy": ["party", "rave", "club", "highenergy"],
            "intimate": ["intimate", "cozy", "small", "personal"],
            "dark humour": ["dark", "sarcasm", "ironic", "brainrot"],
        }

        for reel in reels:
            extraction_data = reel.get("extraction_data") or {}
            text_to_check = json.dumps(extraction_data).lower()

            for vibe, keywords in vibe_keywords.items():
                if any(keyword in text_to_check for keyword in keywords):
                    vibes.add(vibe)

        return sorted(list(vibes))

    def _generate_identity_label(
        self, activities: list[str], aesthetics: list[str], locations: list[str]
    ) -> str | None:
        """Generate a group identity label from profile components."""
        if not activities and not aesthetics and not locations:
            return None

        parts = []
        if aesthetics:
            parts.append(" ".join(aesthetics[:2]).title())
        if activities:
            parts.append(", ".join(activities[:2]).title())
        if locations:
            parts.append("in " + ", ".join(locations[:2]).title())

        if parts:
            return " ".join(parts) + " Vibes"

        return None
