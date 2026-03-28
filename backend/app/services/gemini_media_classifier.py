from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.schemas.media import MediaGeminiClassification, MediaScrapeResponse

REPO_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
GEMINI_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "gemini_system_prompt.json"
GEMINI_EVENT_SEARCH_PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "gemini_event_search_prompt.json"
)
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)


def _load_repo_env_value(key: str) -> str | None:
    if not REPO_ENV_PATH.exists():
        return None

    for raw_line in REPO_ENV_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        env_key, value = line.split("=", 1)
        if env_key.strip() == key:
            return value.strip().strip('"').strip("'")

    return None


def _load_prompt(path: Path) -> str | None:
    if not path.exists():
        return None

    payload = json.loads(path.read_text())
    system_prompt = str(payload.get("system_prompt", "")).strip()
    return system_prompt or None


class GeminiMediaClassifier:
    async def classify(self, payload: MediaScrapeResponse) -> MediaGeminiClassification | None:
        api_key = _load_repo_env_value("GEMINI_API_KEY")
        if not api_key:
            return None

        text_parts: list[str] = []
        if payload.description:
            text_parts.append(f"Fetched video description:\n{payload.description}")

        image_data_urls = [
            frame.image_url
            for frame in payload.frames
            if isinstance(frame.image_url, str) and frame.image_url.startswith("data:")
        ][:8]

        request_parts: list[dict[str, object]] = [{"text": text} for text in text_parts]

        for data_url in image_data_urls:
            header, encoded = data_url.split(",", 1)
            mime_type = header[5:].split(";", 1)[0].strip()
            request_parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": encoded,
                    }
                }
            )

        if not request_parts:
            return None

        request_payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": request_parts}]
        }

        system_prompt = _load_prompt(GEMINI_SYSTEM_PROMPT_PATH)
        if system_prompt:
            request_payload["system_instruction"] = {
                "parts": [{"text": system_prompt}],
            }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{GEMINI_API_URL}?key={api_key}",
                    json=request_payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
        except httpx.HTTPError:
            return None

        body = response.json()
        candidates = body.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        raw_text = "".join(part.get("text", "") for part in parts).strip()
        if not raw_text:
            return None

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            return MediaGeminiClassification(raw_text=raw_text)

        classification = MediaGeminiClassification(
            location=parsed.get("location"),
            event=parsed.get("event"),
            raw_text=raw_text,
        )

        if classification.event is True:
            enriched = await self._enrich_event_details(
                api_key=api_key,
                payload=payload,
                initial=classification,
            )
            if enriched is not None:
                return enriched

        return classification

    async def _enrich_event_details(
        self,
        api_key: str,
        payload: MediaScrapeResponse,
        initial: MediaGeminiClassification,
    ) -> MediaGeminiClassification | None:
        prompt_parts = []
        if initial.location:
            prompt_parts.append(f"Initial identified location: {initial.location}")
        if payload.title:
            prompt_parts.append(f"Video title: {payload.title}")
        if payload.description:
            prompt_parts.append(f"Video description: {payload.description}")
        if payload.user and payload.user.name:
            prompt_parts.append(f"Creator name: {payload.user.name}")
        if payload.user and payload.user.username:
            prompt_parts.append(f"Creator username: {payload.user.username}")

        image_data_urls = [
            frame.image_url
            for frame in payload.frames
            if isinstance(frame.image_url, str) and frame.image_url.startswith("data:")
        ][:8]

        request_parts: list[dict[str, object]] = [
            {"text": "\n\n".join(prompt_parts)}
        ]

        for data_url in image_data_urls:
            header, encoded = data_url.split(",", 1)
            mime_type = header[5:].split(";", 1)[0].strip()
            request_parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": encoded,
                    }
                }
            )

        request_payload: dict[str, object] = {
            "contents": [
                {
                    "role": "user",
                    "parts": request_parts,
                }
            ],
            "tools": [{"google_search": {}}],
        }

        system_prompt = _load_prompt(GEMINI_EVENT_SEARCH_PROMPT_PATH)
        if system_prompt:
            request_payload["system_instruction"] = {
                "parts": [{"text": system_prompt}],
            }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{GEMINI_API_URL}?key={api_key}",
                    json=request_payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
        except httpx.HTTPError:
            return initial

        body = response.json()
        candidates = body.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        raw_text = "".join(part.get("text", "") for part in parts).strip()
        if not raw_text:
            return initial

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            return MediaGeminiClassification(
                location=initial.location,
                event=True,
                price=None,
                time=None,
                raw_text=raw_text,
            )

        return MediaGeminiClassification(
            location=parsed.get("location") or initial.location,
            event=True,
            price=parsed.get("price"),
            time=parsed.get("time"),
            raw_text=raw_text,
        )
