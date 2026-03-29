from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from fastapi import HTTPException, status

from app.config import Settings
from app.schemas.suggestions import (
    Suggestion,
    SuggestionsGenerateRequest,
    SuggestionsGenerateResponse,
)

REPO_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def _load_gemini_api_key() -> str | None:
    # Prefer environment variable (works on Vercel and local dev)
    env_val = os.environ.get("GEMINI_API_KEY")
    if env_val:
        return env_val.strip()
    # Fallback: read from repo-root .env file (local dev only)
    if not REPO_ENV_PATH.exists():
        return None
    for raw_line in REPO_ENV_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        env_key, value = line.split("=", 1)
        if env_key.strip() == "GEMINI_API_KEY":
            return value.strip().strip('"').strip("'")
    return None


class SuggestionsService:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings
        self._supabase_url = str(settings.supabase_url).rstrip("/")
        self._headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        board_id: str,
        user_id: str,
        payload: SuggestionsGenerateRequest,
    ) -> SuggestionsGenerateResponse:
        # 1. Verify the board exists
        await self._verify_board_exists(board_id)

        # 2-4. Fetch context data
        taste_profile = await self._fetch_taste_profile(board_id)
        reels = await self._fetch_reels(board_id, category=payload.category)
        calendar_masks = await self._fetch_calendar_masks(board_id)

        # 5. Build prompt using request-provided swipe IDs
        prompt = self._build_prompt(
            taste_profile=taste_profile,
            reels=reels,
            liked_reel_ids=payload.liked_reel_ids,
            disliked_reel_ids=payload.disliked_reel_ids,
            calendar_masks=calendar_masks,
            count=payload.count,
            category=payload.category,
        )

        raw_suggestions = await self._call_gemini(prompt)

        # 7. Parse and return
        suggestions = self._parse_suggestions(raw_suggestions, payload.count)
        return SuggestionsGenerateResponse(suggestions=suggestions)

    # ===== Data Fetching =====

    async def _verify_board_exists(self, board_id: str) -> None:
        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/boards",
            params={"id": f"eq.{board_id}"},
            headers=self._headers,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not verify board.",
            )
        data = response.json()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found.",
            )

    async def _fetch_taste_profile(self, board_id: str) -> dict | None:
        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/taste_profiles",
            params={"board_id": f"eq.{board_id}"},
            headers=self._headers,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data[0] if data else None

    async def _fetch_reels(
        self, board_id: str, category: str | None = None
    ) -> list[dict]:
        params: dict[str, str | int] = {
            "board_id": f"eq.{board_id}",
            "order": "created_at.desc",
            "limit": 200,
        }
        if category:
            params["classification"] = f"eq.{category}"

        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/reels",
            params=params,
            headers=self._headers,
        )
        if response.status_code != 200:
            return []
        return response.json()

    async def _fetch_calendar_masks(self, board_id: str) -> list[dict]:
        # Get all members of the board first
        members_response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/members",
            params={
                "board_id": f"eq.{board_id}",
                "select": "id",
            },
            headers=self._headers,
        )
        if members_response.status_code != 200:
            return []

        member_ids = [m["id"] for m in members_response.json()]
        if not member_ids:
            return []

        # Fetch calendar masks for all members
        response = await self._http_client.get(
            f"{self._supabase_url}/rest/v1/calendar_masks",
            params={
                "member_id": f"in.({','.join(member_ids)})",
            },
            headers=self._headers,
        )
        if response.status_code != 200:
            return []
        return response.json()

    # ===== Prompt Building =====

    def _build_prompt(
        self,
        taste_profile: dict | None,
        reels: list[dict],
        liked_reel_ids: list[str],
        disliked_reel_ids: list[str],
        calendar_masks: list[dict],
        count: int,
        category: str | None,
    ) -> str:
        # Build swipe lookup from request-provided IDs
        swipe_map: dict[str, str] = {}
        for reel_id in liked_reel_ids:
            swipe_map[reel_id] = "right"
        for reel_id in disliked_reel_ids:
            swipe_map[reel_id] = "left"

        # Taste profile section
        profile_section = "No taste profile available yet."
        if taste_profile:
            profile_data = taste_profile.get("profile_data") or taste_profile
            parts = []
            for key in [
                "activity_types",
                "food_preferences",
                "aesthetic_register",
                "location_patterns",
                "price_range",
                "vibe_tags",
            ]:
                val = profile_data.get(key)
                if val:
                    parts.append(f"- {key}: {val}")
            identity = profile_data.get("identity_label") or taste_profile.get(
                "identity_label"
            )
            if identity:
                parts.append(f"- Group identity: {identity}")
            if parts:
                profile_section = "\n".join(parts)

        # Reel summaries
        liked_reels: list[str] = []
        disliked_reels: list[str] = []
        neutral_reels: list[str] = []
        reel_ids_in_context: list[str] = []

        for reel in reels:
            reel_id = reel.get("id", "")
            reel_ids_in_context.append(reel_id)
            extraction = reel.get("extraction_data") or {}
            summary_parts = []
            if isinstance(extraction, dict):
                for field in [
                    "title",
                    "venue_name",
                    "cuisine",
                    "location",
                    "price",
                    "vibe",
                ]:
                    v = extraction.get(field)
                    if v:
                        summary_parts.append(f"{field}={v}")
            classification = reel.get("classification", "unknown")
            summary = (
                f"[{reel_id}] classification={classification} "
                + " ".join(summary_parts)
            )

            direction = swipe_map.get(reel_id)
            if direction == "right":
                liked_reels.append(summary)
            elif direction == "left":
                disliked_reels.append(summary)
            else:
                neutral_reels.append(summary)

        reels_section = ""
        if liked_reels:
            reels_section += "LIKED reels (weight these HIGHER):\n"
            reels_section += "\n".join(liked_reels[:50]) + "\n\n"
        if disliked_reels:
            reels_section += "DISLIKED reels (weight these LOWER):\n"
            reels_section += "\n".join(disliked_reels[:30]) + "\n\n"
        if neutral_reels:
            reels_section += "Unswiped reels:\n"
            reels_section += "\n".join(neutral_reels[:30]) + "\n\n"

        if not reels_section:
            reels_section = "No reels available.\n"

        # Calendar availability
        calendar_section = "No calendar data available."
        if calendar_masks:
            busy_summaries = []
            for mask in calendar_masks:
                busy = mask.get("busy_slots")
                if busy:
                    busy_summaries.append(json.dumps(busy))
            if busy_summaries:
                calendar_section = (
                    "Members' busy slots (avoid these times):\n"
                    + "\n".join(busy_summaries[:10])
                )

        # Date context
        today = datetime.utcnow()
        next_14_days = today + timedelta(days=14)
        date_context = (
            f"Today is {today.strftime('%A %d %B %Y')}. "
            f"Prioritise suggestions within the next 14 days (up to {next_14_days.strftime('%A %d %B %Y')})."
        )

        category_instruction = ""
        if category:
            category_instruction = (
                f"\nFocus on the '{category}' category for all suggestions."
            )

        return f"""You are a group activity recommendation engine for a friend group.
Generate exactly {count} DISTINCT activity suggestions based on the group's taste profile and reel history.

RULES:
- Each suggestion must be a SPECIFIC, ACTIONABLE plan (real venue names, real dates/times, real prices).
- Every suggestion must be DISTINCT from the others (different type of activity, different venue, different vibe).
- Weight liked reels much higher than disliked ones when choosing what to suggest.
- Prioritise real upcoming events within the next 14 days.
- Avoid times when members are busy (see calendar data below).
- The "influenced_by" field must list reel IDs that inspired each suggestion.
- Return ONLY valid JSON, no markdown fences, no extra text.
{category_instruction}

{date_context}

=== GROUP TASTE PROFILE ===
{profile_section}

=== REEL HISTORY ===
{reels_section}

=== CALENDAR AVAILABILITY ===
{calendar_section}

=== RESPONSE FORMAT ===
Return a JSON array of exactly {count} objects, each with these fields:
{{
  "what": "Short activity title",
  "why": "1-2 sentence explanation referencing group tastes/reels",
  "where": "Specific venue/location with address if possible",
  "when": "Specific date and time suggestion",
  "cost_per_person": "Estimated cost range per person (e.g. £25-35)",
  "booking_url": "URL if known, otherwise null",
  "influenced_by": ["reel_id_1", "reel_id_2"],
  "category": "real_event|real_venue|recipe_food|vibe_inspiration|humour_identity",
  "confidence": 0.85
}}"""

    # ===== Gemini API =====

    async def _call_gemini(self, prompt: str) -> str:
        api_key = _load_gemini_api_key()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini API key not configured.",
            )

        request_payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.9,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{GEMINI_API_URL}?key={api_key}",
                    json=request_payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini API request failed: {exc}",
            )

        body = response.json()
        candidates = body.get("candidates") or []
        parts = (
            candidates[0].get("content", {}).get("parts", []) if candidates else []
        )
        raw_text = "".join(part.get("text", "") for part in parts).strip()
        if not raw_text:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Empty response from Gemini.",
            )
        return raw_text

    # ===== Response Parsing =====

    def _parse_suggestions(
        self, raw_text: str, count: int
    ) -> list[Suggestion]:
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not parse Gemini response as JSON.",
            )

        # Handle both bare array and {"suggestions": [...]} wrapper
        if isinstance(parsed, dict):
            parsed = parsed.get("suggestions", [])

        if not isinstance(parsed, list):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unexpected Gemini response structure.",
            )

        suggestions: list[Suggestion] = []
        for item in parsed[:count]:
            if not isinstance(item, dict):
                continue
            suggestions.append(
                Suggestion(
                    what=item.get("what", "Activity suggestion"),
                    why=item.get("why", ""),
                    where=item.get("where"),
                    when=item.get("when"),
                    cost_per_person=item.get("cost_per_person"),
                    booking_url=item.get("booking_url"),
                    influenced_by=item.get("influenced_by", []),
                    category=item.get("category", "vibe_inspiration"),
                    confidence=min(max(float(item.get("confidence", 0.5)), 0.0), 1.0),
                )
            )

        return suggestions
