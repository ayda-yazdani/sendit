from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, field_validator


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MediaScrapeRequest(StrictRequestModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        validated = TypeAdapter(AnyHttpUrl).validate_python(value)
        if validated.scheme != "https":
            raise ValueError("URL must use https.")
        return str(validated)


class MediaUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    username: str | None = None
    profile_url: AnyHttpUrl | None = None


class MediaFrame(BaseModel):
    image_url: str
    timestamp_seconds: float
    timestamp_text: str


class MediaGeminiClassification(BaseModel):
    location: str | None = None
    event: bool | None = None
    price: str | None = None
    time: str | None = None
    raw_text: str | None = None


class MediaScrapeResponse(BaseModel):
    platform: Literal["instagram", "tiktok", "youtube"]
    requested_url: AnyHttpUrl
    resolved_url: AnyHttpUrl | None = None
    canonical_url: AnyHttpUrl | None = None
    media_id: str | None = None
    title: str | None = None
    description: str | None = None
    cover_image_url: AnyHttpUrl | None = None
    preview_image_urls: list[AnyHttpUrl] = Field(default_factory=list)
    frames: list[MediaFrame] = Field(default_factory=list)
    video_url: AnyHttpUrl | None = None
    embed_url: AnyHttpUrl | None = None
    post_date: datetime | None = None
    duration: str | None = None
    user: MediaUser | None = None
    price: str | None = None
    time: str | None = None
    gemini: MediaGeminiClassification | None = None
