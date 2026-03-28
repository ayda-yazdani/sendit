from datetime import datetime
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class ReelCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str
    platform: Literal["youtube", "instagram", "tiktok", "x", "other"]


class ReelResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    board_id: str
    added_by: str
    url: str
    platform: Literal["youtube", "instagram", "tiktok", "x", "other"]
    classification: Literal[
        "real_event", "real_venue", "vibe_inspiration", "recipe_food", "humour_identity"
    ] | None = None
    extraction_data: dict[str, Any] | None = None
    created_at: datetime


class ReelsListResponse(BaseModel):
    reels: list[ReelResponse] = Field(default_factory=list)
    total: int = 0
    board_id: str


class ReelDeleteResponse(BaseModel):
    success: bool
    message: str
