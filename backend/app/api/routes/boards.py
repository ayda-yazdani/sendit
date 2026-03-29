from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.dependencies import (
    get_verified_user,
    get_boards_service,
    get_instagram_reel_scraper_service,
    get_tiktok_video_scraper_service,
    get_youtube_shorts_scraper_service,
)
from app.schemas.auth import SupabaseUser
from app.schemas.boards import (
    ReelCreateRequest,
    ReelDeleteResponse,
    ReelsListResponse,
    BoardCreateRequest,
    BoardResponse,
    BoardListResponse,
    BoardJoinRequest,
    MemberCreateRequest,
    MemberResponse,
    MembersListResponse,
    MemberUpdateRequest,
    TasteProfileResponse,
    TasteProfileSyncRequest,
    TasteProfileUpdateRequest,
)
from app.services.boards import BoardsService
from app.services.instagram import InstagramReelScraperService
from app.services.media import MediaScraperService
from app.services.gemini_media_classifier import GeminiMediaClassifier
from app.services.tiktok import TikTokVideoScraperService
from app.services.youtube import YouTubeShortsScraperService


router = APIRouter(prefix="/boards", tags=["boards"])


# ===== BOARD MANAGEMENT ENDPOINTS =====


@router.post(
    "",
    response_model=BoardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_board(
    payload: BoardCreateRequest,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> BoardResponse:
    """
    Create a new board.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    - Body: BoardCreateRequest with name and display_name
    """
    # Use user ID as device_id for now (can be updated later)
    device_id = _.id
    return await service.create_board(payload=payload, user_device_id=device_id)


@router.get(
    "",
    response_model=BoardListResponse,
)
async def list_user_boards(
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> BoardListResponse:
    """
    List all boards the user is a member of.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    device_id = _.id
    return await service.list_user_boards(user_device_id=device_id)


@router.get(
    "/{board_id}",
    response_model=BoardResponse,
)
async def get_board(
    board_id: str,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> BoardResponse:
    """
    Get board details with member count.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    return await service.get_board(board_id=board_id)


@router.post(
    "/join",
    response_model=BoardResponse,
)
async def join_board(
    payload: BoardJoinRequest,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> BoardResponse:
    """
    Join a board using the join code.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    - Body: BoardJoinRequest with join_code and display_name
    """
    device_id = _.id
    return await service.join_board(payload=payload, user_device_id=device_id)


@router.delete(
    "/{board_id}",
    response_model=dict,
)
async def delete_board(
    board_id: str,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> dict:
    """
    Delete a board and all its associated data.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    return await service.delete_board(board_id=board_id)


# ===== MEMBER MANAGEMENT ENDPOINTS =====


@router.get(
    "/{board_id}/members",
    response_model=MembersListResponse,
)
async def list_board_members(
    board_id: str,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
    limit: int = 100,
    offset: int = 0,
) -> MembersListResponse:
    """
    List all members in a board.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    return await service.list_board_members(
        board_id=board_id, limit=limit, offset=offset
    )


@router.patch(
    "/{board_id}/members/{member_id}",
    response_model=MemberResponse,
)
async def update_member_profile(
    board_id: str,
    member_id: str,
    payload: MemberUpdateRequest,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> MemberResponse:
    """
    Update a member's profile (display_name, avatar_url).
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    return await service.update_member_profile(
        board_id=board_id, member_id=member_id, payload=payload
    )


@router.delete(
    "/{board_id}/members/{member_id}",
    response_model=dict,
)
async def delete_member_from_board(
    board_id: str,
    member_id: str,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> dict:
    """
    Remove a member from a board.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    return await service.delete_member_from_board(
        board_id=board_id, member_id=member_id
    )


# ===== REEL MANAGEMENT ENDPOINTS =====


@router.get(
    "/{board_id}/reels",
    response_model=ReelsListResponse,
)
async def list_board_reels(
    board_id: str,
    member_id: str = Header(None, alias="x-member-id"),
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
    limit: int = 100,
    offset: int = 0,
) -> ReelsListResponse:
    """
    List all reels in a board.
    
    Requires:
    - x-member-id header: The member ID of the user in this board
    - Authentication: Bearer token in Authorization header
    """
    if not member_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-member-id header is required.",
        )
    return await service.list_reels_in_board(
        board_id=board_id, limit=limit, offset=offset
    )


@router.post(
    "/{board_id}/reels",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def add_reel_to_board(
    board_id: str,
    payload: ReelCreateRequest,
    member_id: str = Header(None, alias="x-member-id"),
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> dict:
    """
    Add a reel to a board.
    
    Requires:
    - x-member-id header: The member ID of the user in this board
    - Authentication: Bearer token in Authorization header
    - Body: ReelCreateRequest with url and platform
    """
    if not member_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-member-id header is required.",
        )
    reel = await service.add_reel_to_board(
        board_id=board_id, member_id=member_id, payload=payload
    )
    return {
        "success": True,
        "message": "Reel added to board.",
        "reel": reel.model_dump(),
    }


@router.delete(
    "/{board_id}/reels/{reel_id}",
    response_model=ReelDeleteResponse,
)
async def delete_reel_from_board(
    board_id: str,
    reel_id: str,
    member_id: str = Header(None, alias="x-member-id"),
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> ReelDeleteResponse:
    """
    Delete a reel from a board.
    
    Requires:
    - x-member-id header: The member ID of the user in this board
    - Authentication: Bearer token in Authorization header
    """
    if not member_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-member-id header is required.",
        )
    result = await service.delete_reel_from_board(
        board_id=board_id, reel_id=reel_id
    )
    return ReelDeleteResponse(**result)


# ===== TASTE PROFILE ENDPOINTS =====


@router.get(
    "/{board_id}/taste-profile",
    response_model=TasteProfileResponse,
)
async def get_taste_profile(
    board_id: str,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> TasteProfileResponse:
    """
    Get the taste profile for a board.
    
    Returns aggregated taste data including activity types, aesthetic register,
    food preferences, location patterns, price range, and group identity label.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    """
    return await service.get_taste_profile(board_id=board_id)


@router.post(
    "/{board_id}/taste-profile/sync",
    response_model=TasteProfileResponse,
)
async def sync_taste_profile(
    board_id: str,
    payload: TasteProfileSyncRequest,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> TasteProfileResponse:
    """
    Generate or regenerate the taste profile for a board.
    
    Analyzes all reels on the board and generates aggregated profile data.
    Includes activity types, aesthetic tags, food preferences, locations,
    price range estimates, vibe tags, and AI-generated group identity label.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    - Body: TasteProfileSyncRequest with optional force flag
    """
    return await service.sync_taste_profile(board_id=board_id, payload=payload)


@router.patch(
    "/{board_id}/taste-profile",
    response_model=TasteProfileResponse,
)
async def update_taste_profile(
    board_id: str,
    payload: TasteProfileUpdateRequest,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
) -> TasteProfileResponse:
    """
    Manually update specific fields in a taste profile.
    
    Allows manual refinement of auto-generated taste profile data.
    Any fields not provided will remain unchanged.
    
    Requires:
    - Authentication: Bearer token in Authorization header
    - Body: TasteProfileUpdateRequest with fields to update
    """
    return await service.update_taste_profile(board_id=board_id, payload=payload)


# ===== RECLASSIFY ENDPOINT =====


@router.post("/{board_id}/reclassify")
async def reclassify_reels(
    board_id: str,
    _: SupabaseUser = Depends(get_verified_user),
    service: BoardsService = Depends(get_boards_service),
    instagram_service: InstagramReelScraperService = Depends(get_instagram_reel_scraper_service),
    tiktok_service: TikTokVideoScraperService = Depends(get_tiktok_video_scraper_service),
    youtube_service: YouTubeShortsScraperService = Depends(get_youtube_shorts_scraper_service),
) -> dict:
    """Re-scrape and reclassify all unclassified reels in a board."""
    scraper = MediaScraperService(
        instagram_service=instagram_service,
        tiktok_service=tiktok_service,
        youtube_service=youtube_service,
        gemini_classifier=GeminiMediaClassifier(),
    )
    return await service.reclassify_board_reels(board_id=board_id, scraper_service=scraper)
