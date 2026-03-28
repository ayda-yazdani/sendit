from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, computed_field, field_validator


class InstagramAuthor(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    username: str | None = None
    profile_url: AnyHttpUrl | None = None


class InstagramReelScrapeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str

    @field_validator("url")
    @classmethod
    def validate_reel_url(cls, value: str) -> str:
        validated = TypeAdapter(AnyHttpUrl).validate_python(value)
        if validated.scheme != "https":
            raise ValueError("URL must use https.")
        allowed_hosts = {"instagram.com", "www.instagram.com", "m.instagram.com"}
        if validated.host not in allowed_hosts:
            raise ValueError("URL must point to an Instagram reel.")
        if not validated.path.startswith("/reel/"):
            raise ValueError("URL must point to an Instagram reel.")
        return str(validated)


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

    @computed_field(return_type=AnyHttpUrl | None)
    @property
    def cover_image_url(self) -> AnyHttpUrl | None:
        return self.thumbnail_url

    @computed_field(return_type=datetime | None)
    @property
    def post_date(self) -> datetime | None:
        return self.published_at

    @computed_field(return_type=InstagramAuthor | None)
    @property
    def user(self) -> InstagramAuthor | None:
        return self.author
