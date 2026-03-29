import uuid
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder

from app.config import Settings
from app.schemas.media import MediaScrapeResponse


class MediaScrapeHistoryService:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings
        self._supabase_url = str(settings.supabase_url).rstrip("/")
        self._headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    async def record_scrape(
        self,
        *,
        user_id: str,
        requested_url: str,
        response_payload: MediaScrapeResponse,
    ) -> None:
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "requested_url": requested_url,
            "platform": response_payload.platform,
            "media_id": response_payload.media_id,
            "canonical_url": response_payload.canonical_url,
            "response_data": jsonable_encoder(response_payload),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        response = await self._http_client.post(
            f"{self._supabase_url}/rest/v1/media_scrapes",
            json=record,
            headers=self._headers,
        )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not persist media scrape.",
            )
