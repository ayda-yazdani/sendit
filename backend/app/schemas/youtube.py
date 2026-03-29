from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, computed_field, field_validator

from app.schemas.media import MediaFrame


class YouTubeChannel(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    handle: str | None = None
    channel_id: str | None = None
    channel_url: AnyHttpUrl | None = None


class YouTubeShortScrapeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str

    @field_validator("url")
    @classmethod
    def validate_shorts_url(cls, value: str) -> str:
        validated = TypeAdapter(AnyHttpUrl).validate_python(value)
        if validated.scheme != "https":
            raise ValueError("URL must use https.")
        allowed_hosts = {"youtube.com", "www.youtube.com", "m.youtube.com"}
        if validated.host not in allowed_hosts:
            raise ValueError("URL must point to a YouTube Shorts video.")
        if not validated.path.startswith("/shorts/"):
            raise ValueError("URL must point to a YouTube Shorts video.")
        return str(validated)


class YouTubeShortScrapeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    requested_url: AnyHttpUrl
    resolved_url: AnyHttpUrl | None = None
    canonical_url: AnyHttpUrl | None = None
    short_id: str | None = None
    title: str | None = None
    description: str | None = None
    thumbnail_url: AnyHttpUrl | None = None
    preview_image_urls: list[AnyHttpUrl] = Field(default_factory=list)
    frames: list[MediaFrame] = Field(default_factory=list)
    video_url: AnyHttpUrl | None = None
    embed_url: AnyHttpUrl | None = None
    site_name: str | None = None
    channel: YouTubeChannel | None = None
    published_at: datetime | None = None
    duration: str | None = None
    open_graph: dict[str, str] = Field(default_factory=dict)
    json_ld: list[dict[str, Any]] = Field(default_factory=list)

    @computed_field(return_type=AnyHttpUrl | None)
    @property
    def cover_image_url(self) -> AnyHttpUrl | None:
        return self.thumbnail_url

    @computed_field(return_type=datetime | None)
    @property
    def post_date(self) -> datetime | None:
        return self.published_at

    @computed_field(return_type=YouTubeChannel | None)
    @property
    def user(self) -> YouTubeChannel | None:
        return self.channel
