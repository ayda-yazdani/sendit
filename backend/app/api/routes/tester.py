from pathlib import Path
import base64
import json

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse

router = APIRouter(tags=["tester"])

TESTER_HTML_PATH = (
    Path(__file__).resolve().parents[2] / "static" / "tester" / "dist" / "index.html"
)
REPO_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
GEMINI_SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "gemini_system_prompt.json"
)
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-lite:generateContent"
)


class GeminiPromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    text_parts: list[str] = Field(default_factory=list, max_length=12)
    image_data_urls: list[str] = Field(default_factory=list, max_length=8)


class GeminiPromptResponse(BaseModel):
    text: str
    model: str = "gemini-2.5-flash-lite"
    request_payload: dict[str, object] | None = None


class GeminiConfigResponse(BaseModel):
    model: str = "gemini-2.5-flash-lite"
    system_prompt: str | None = None


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


def _load_gemini_system_prompt() -> str | None:
    if not GEMINI_SYSTEM_PROMPT_PATH.exists():
        return None

    try:
        payload = json.loads(GEMINI_SYSTEM_PROMPT_PATH.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Gemini system prompt JSON is invalid.",
        ) from exc

    system_prompt = str(payload.get("system_prompt", "")).strip()
    return system_prompt or None


def _build_gemini_parts(payload: GeminiPromptRequest) -> list[dict[str, object]]:
    parts: list[dict[str, object]] = []

    text_parts = [part.strip() for part in payload.text_parts if part.strip()]
    if text_parts:
        parts.extend({"text": part} for part in text_parts)
    elif payload.prompt.strip():
        parts.append({"text": payload.prompt.strip()})

    for image_data_url in payload.image_data_urls:
        data_url = image_data_url.strip()
        if not data_url:
            continue
        if not data_url.startswith("data:") or "," not in data_url:
            raise HTTPException(status_code=422, detail="Invalid image data URL.")

        header, encoded = data_url.split(",", 1)
        if ";base64" not in header:
            raise HTTPException(status_code=422, detail="Images must be base64 data URLs.")

        mime_type = header[5:].split(";", 1)[0].strip()
        if not mime_type.startswith("image/"):
            raise HTTPException(status_code=422, detail="Only image uploads are supported.")

        try:
            base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Invalid base64 image payload.") from exc

        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": encoded,
                }
            }
        )

    return parts


@router.get("/", response_class=FileResponse)
async def tester_page() -> FileResponse:
    if not TESTER_HTML_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Tester frontend build is missing. Run "
                "`cd backend/tester-app && npm install && npm run build`."
            ),
        )
    return FileResponse(TESTER_HTML_PATH)


@router.get("/tester/gemini-config", response_model=GeminiConfigResponse)
async def tester_gemini_config() -> GeminiConfigResponse:
    return GeminiConfigResponse(system_prompt=_load_gemini_system_prompt())


@router.post("/tester/gemini", response_model=GeminiPromptResponse)
async def tester_gemini_prompt(payload: GeminiPromptRequest) -> GeminiPromptResponse:
    api_key = _load_repo_env_value("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is missing from the repo .env file.",
        )

    request_payload = {"contents": [{"role": "user", "parts": _build_gemini_parts(payload)}]}
    system_prompt = _load_gemini_system_prompt()
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
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {str(exc)}",
        ) from exc

    body = response.json()
    if response.status_code >= 400:
        detail = body.get("error", {}).get("message") or "Gemini request failed."
        raise HTTPException(status_code=response.status_code, detail=detail)

    candidates = body.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    text = "".join(part.get("text", "") for part in parts).strip()

    if not text:
        raise HTTPException(
            status_code=502,
            detail="Gemini returned no text content.",
        )

    return GeminiPromptResponse(text=text, request_payload=request_payload)
