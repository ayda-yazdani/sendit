from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class InstagramAuthor(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    username: str | None = None
    profile_url: AnyHttpUrl | None = None


class InstagramReelScrapeRequest(BaseModel):
    url: AnyHttpUrl

    @field_validator("url")
    @classmethod
    def validate_reel_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        allowed_hosts = {"instagram.com", "www.instagram.com", "m.instagram.com"}
        if value.host not in allowed_hosts:
            raise ValueError("URL must point to an Instagram reel.")
        if not value.path.startswith("/reel/"):
            raise ValueError("URL must point to an Instagram reel.")
        return value


class InstagramReelScrapeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    requested_url: AnyHttpUrl
    resolved_url: AnyHttpUrl | None = None
    canonical_url: AnyHttpUrl | None = None
    reel_id: str | None = None
    title: str | None = None
    description: str | None = None
    thumbnail_url: AnyHttpUrl | None = None
    video_url: AnyHttpUrl | None = None
    embed_url: AnyHttpUrl | None = None
    site_name: str | None = None
    author: InstagramAuthor | None = None
    published_at: datetime | None = None
    duration: str | None = None
    open_graph: dict[str, str] = Field(default_factory=dict)
    json_ld: list[dict[str, Any]] = Field(default_factory=list)
