from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.dependencies import get_verified_user, get_boards_service
from app.schemas.auth import SupabaseUser
from app.schemas.boards import (
    ReelCreateRequest,
    ReelDeleteResponse,
    ReelsListResponse,
)
from app.services.boards import BoardsService


router = APIRouter(prefix="/boards", tags=["boards"])


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
