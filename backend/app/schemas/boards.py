from datetime import datetime
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, EmailStr


class BoardCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str
    display_name: str = Field(
        description="The display name for the creator in this board"
    )


class BoardResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    join_code: str
    member_count: int = 1
    created_at: datetime


class BoardListResponse(BaseModel):
    boards: list[BoardResponse] = Field(default_factory=list)
    total: int = 0


class MemberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str


class MemberUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str | None = None
    avatar_url: str | None = None


class MemberResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    board_id: str
    display_name: str
    device_id: str
    google_id: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None


class MembersListResponse(BaseModel):
    members: list[MemberResponse] = Field(default_factory=list)
    total: int = 0
    board_id: str


class BoardJoinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    join_code: str
    display_name: str


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
