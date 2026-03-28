from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class MediaScrapeRequest(BaseModel):
    url: AnyHttpUrl


class MediaUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    username: str | None = None
    profile_url: AnyHttpUrl | None = None


class MediaScrapeResponse(BaseModel):
    platform: Literal["instagram", "tiktok", "youtube"]
    requested_url: AnyHttpUrl
    resolved_url: AnyHttpUrl | None = None
    canonical_url: AnyHttpUrl | None = None
    media_id: str | None = None
    title: str | None = None
    description: str | None = None
    cover_image_url: AnyHttpUrl | None = None
    video_url: AnyHttpUrl | None = None
    embed_url: AnyHttpUrl | None = None
    post_date: datetime | None = None
    duration: str | None = None
    user: MediaUser | None = None
