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


# ===== TASTE PROFILE SCHEMAS =====


class TasteProfileResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    board_id: str
    activity_types: list[str] = Field(
        default_factory=list,
        description="Types of activities the group enjoys (e.g., dining, nightlife, music)",
    )
    aesthetic_register: list[str] = Field(
        default_factory=list,
        description="How the group describes things (e.g., underground, upscale, casual)",
    )
    food_preferences: list[str] = Field(
        default_factory=list,
        description="Food types and cuisines the group likes",
    )
    location_patterns: list[str] = Field(
        default_factory=list,
        description="Areas and neighborhoods the group frequents",
    )
    price_range: str | None = Field(
        default=None, description="Estimated spending per person (e.g., £15-30)"
    )
    vibe_tags: list[str] = Field(
        default_factory=list,
        description="General vibes and moods (e.g., dark humour, intimate, high energy)",
    )
    identity_label: str | None = Field(
        default=None, description="AI-generated group identity label"
    )
    reel_count: int = Field(
        default=0, description="Number of reels used to build this profile"
    )
    updated_at: datetime
    created_at: datetime


class TasteProfileSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = Field(
        default=False, description="Force regenerate even if recently updated"
    )


class TasteProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    activity_types: list[str] | None = None
    aesthetic_register: list[str] | None = None
    food_preferences: list[str] | None = None
    location_patterns: list[str] | None = None
    price_range: str | None = None
    vibe_tags: list[str] | None = None
    identity_label: str | None = None


# ===== USER PROFILE SCHEMAS =====


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    device_id: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = Field(
        default=None, description="User's personal bio or status message"
    )
    created_at: datetime
    updated_at: datetime


class UserProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(description="User's display name")
    avatar_url: str | None = Field(default=None, description="Avatar image URL")
    bio: str | None = Field(default=None, description="Personal bio or status")


class UserProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
