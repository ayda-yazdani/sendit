from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SuggestionsGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: Literal[
        "real_event", "real_venue", "recipe_food", "vibe_inspiration", "humour_identity"
    ] | None = Field(default=None, description="Filter reels by classification category")
    count: int = Field(default=5, ge=1, le=20, description="Number of suggestions to generate")


class Suggestion(BaseModel):
    what: str
    why: str
    where: str | None = None
    when: str | None = None
    cost_per_person: str | None = None
    booking_url: str | None = None
    influenced_by: list[str] = Field(default_factory=list)
    category: str
    confidence: float = Field(ge=0.0, le=1.0)


class SuggestionsGenerateResponse(BaseModel):
    suggestions: list[Suggestion] = Field(default_factory=list)
