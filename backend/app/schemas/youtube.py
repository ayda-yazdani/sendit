from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class YouTubeChannel(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    handle: str | None = None
    channel_id: str | None = None
    channel_url: AnyHttpUrl | None = None


class YouTubeShortScrapeRequest(BaseModel):
    url: AnyHttpUrl

    @field_validator("url")
    @classmethod
    def validate_shorts_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        allowed_hosts = {"youtube.com", "www.youtube.com", "m.youtube.com"}
        if value.host not in allowed_hosts:
            raise ValueError("URL must point to a YouTube Shorts video.")
        if not value.path.startswith("/shorts/"):
            raise ValueError("URL must point to a YouTube Shorts video.")
        return value


class YouTubeShortScrapeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    requested_url: AnyHttpUrl
    resolved_url: AnyHttpUrl | None = None
    canonical_url: AnyHttpUrl | None = None
    short_id: str | None = None
    title: str | None = None
    description: str | None = None
    thumbnail_url: AnyHttpUrl | None = None
    video_url: AnyHttpUrl | None = None
    embed_url: AnyHttpUrl | None = None
    site_name: str | None = None
    channel: YouTubeChannel | None = None
    published_at: datetime | None = None
    duration: str | None = None
    open_graph: dict[str, str] = Field(default_factory=dict)
    json_ld: list[dict[str, Any]] = Field(default_factory=list)
