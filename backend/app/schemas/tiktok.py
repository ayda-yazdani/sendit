from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, computed_field, field_validator


class TikTokAuthor(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    username: str | None = None
    profile_url: AnyHttpUrl | None = None


class TikTokVideoScrapeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str

    @field_validator("url")
    @classmethod
    def validate_tiktok_url(cls, value: str) -> str:
        validated = TypeAdapter(AnyHttpUrl).validate_python(value)
        if validated.scheme != "https":
            raise ValueError("URL must use https.")
        allowed_hosts = {
            "tiktok.com",
            "www.tiktok.com",
            "m.tiktok.com",
            "vm.tiktok.com",
            "vt.tiktok.com",
        }
        if validated.host not in allowed_hosts:
            raise ValueError("URL must point to a TikTok video.")

        short_link_hosts = {"vm.tiktok.com", "vt.tiktok.com"}
        if validated.host in short_link_hosts:
            return str(validated)

        if "/video/" not in validated.path:
            raise ValueError("URL must point to a TikTok video.")

        return str(validated)


class TikTokVideoScrapeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    requested_url: AnyHttpUrl
    resolved_url: AnyHttpUrl | None = None
    canonical_url: AnyHttpUrl | None = None
    video_id: str | None = None
    title: str | None = None
    description: str | None = None
    thumbnail_url: AnyHttpUrl | None = None
    video_url: AnyHttpUrl | None = None
    embed_url: AnyHttpUrl | None = None
    site_name: str | None = None
    author: TikTokAuthor | None = None
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

    @computed_field(return_type=TikTokAuthor | None)
    @property
    def user(self) -> TikTokAuthor | None:
        return self.author
