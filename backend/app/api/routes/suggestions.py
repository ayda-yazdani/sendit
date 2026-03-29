from fastapi import APIRouter, Depends

from app.dependencies import get_suggestions_service, get_verified_user
from app.schemas.auth import SupabaseUser
from app.schemas.suggestions import (
    SuggestionsGenerateRequest,
    SuggestionsGenerateResponse,
)
from app.services.suggestions import SuggestionsService

router = APIRouter(prefix="/boards/{board_id}/suggestions", tags=["suggestions"])


@router.post("/generate", response_model=SuggestionsGenerateResponse)
async def generate_suggestions(
    board_id: str,
    payload: SuggestionsGenerateRequest,
    user: SupabaseUser = Depends(get_verified_user),
    service: SuggestionsService = Depends(get_suggestions_service),
) -> SuggestionsGenerateResponse:
    return await service.generate(
        board_id=board_id,
        user_id=user.id,
        payload=payload,
    )
