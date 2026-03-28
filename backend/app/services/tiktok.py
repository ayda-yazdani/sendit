import json
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.schemas.tiktok import (
    TikTokAuthor,
    TikTokVideoScrapeRequest,
    TikTokVideoScrapeResponse,
)
from app.services.social_scrape import (
    DEFAULT_SCRAPE_USER_AGENT,
    MetadataHTMLParser,
    extract_open_graph,
    parse_json_ld_blocks,
    pick_primary_object,
    pick_string,
    pick_thumbnail,
)


class TikTokVideoScraperService:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def scrape_video(
        self, payload: TikTokVideoScrapeRequest
    ) -> TikTokVideoScrapeResponse:
        try:
            response = await self._http_client.get(
                str(payload.url),
                follow_redirects=True,
                headers={
                    "User-Agent": DEFAULT_SCRAPE_USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Timed out while fetching the TikTok video.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch the TikTok video.",
            ) from exc

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TikTok video not found.",
            )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="TikTok returned an error while fetching the video.",
            )

        parser = MetadataHTMLParser()
        parser.feed(response.text)

        open_graph = extract_open_graph(parser.meta_tags)
        json_ld_documents = parse_json_ld_blocks(parser.json_ld_blocks)
        primary_video = pick_primary_object(
            json_ld_documents, preferred_types=("VideoObject", "SocialMediaPosting")
        )
        detail_payload = self._extract_video_detail_payload(response.text)
        item_payload = self._extract_item_payload(detail_payload)

        video_id = self._extract_video_id(str(response.url))
        title = (
            open_graph.get("og:title")
            or pick_string(primary_video, "name")
            or self._extract_share_meta(detail_payload, "title")
        )
        description = (
            open_graph.get("og:description")
            or pick_string(primary_video, "description")
            or self._extract_tiktok_description(item_payload)
            or self._extract_share_meta(detail_payload, "desc")
        )
        thumbnail_url = (
            open_graph.get("og:image")
            or pick_thumbnail(primary_video)
            or self._extract_video_field(item_payload, "cover")
        )
        video_url = (
            open_graph.get("og:video")
            or open_graph.get("og:video:url")
            or pick_string(primary_video, "contentUrl")
            or self._extract_video_field(item_payload, "playAddr")
        )
        if video_id is None:
            video_id = self._extract_item_string(item_payload, "id")

        if not any(
            [
                title,
                description,
                thumbnail_url,
                video_url,
                open_graph,
                json_ld_documents,
                item_payload,
            ]
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not extract TikTok video metadata from the response.",
            )

        return TikTokVideoScrapeResponse(
            requested_url=payload.url,
            resolved_url=str(response.url),
            canonical_url=(
                open_graph.get("og:url")
                or parser.canonical_url
                or self._build_canonical_url(item_payload, video_id)
            ),
            video_id=video_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            video_url=video_url,
            embed_url=pick_string(primary_video, "embedUrl")
            or self._build_embed_url(video_id),
            site_name=open_graph.get("og:site_name"),
            author=self._extract_author(primary_video, item_payload),
            published_at=pick_string(primary_video, "uploadDate")
            or pick_string(primary_video, "datePublished")
            or self._extract_published_at(item_payload),
            duration=pick_string(primary_video, "duration")
            or self._extract_duration(item_payload),
            open_graph=open_graph,
            json_ld=json_ld_documents,
        )

    def _extract_author(
        self,
        primary_video: dict[str, object] | None,
        item_payload: dict[str, Any] | None,
    ) -> TikTokAuthor | None:
        if not isinstance(primary_video, dict):
            return self._extract_author_from_item(item_payload)

        author_payload = primary_video.get("author")
        if not isinstance(author_payload, dict):
            return self._extract_author_from_item(item_payload)

        profile_url = author_payload.get("url")
        profile_url = profile_url if isinstance(profile_url, str) else None
        username = self._extract_username(profile_url)
        if username is None:
            alternate_name = pick_string(author_payload, "alternateName")
            if alternate_name and alternate_name.startswith("@"):
                username = alternate_name.lstrip("@")

        return TikTokAuthor(
            name=pick_string(author_payload, "name"),
            username=username,
            profile_url=profile_url,
        )

    def _extract_author_from_item(
        self, item_payload: dict[str, Any] | None
    ) -> TikTokAuthor | None:
        if not isinstance(item_payload, dict):
            return None

        author_payload = item_payload.get("author")
        if not isinstance(author_payload, dict):
            return None

        username = self._extract_item_string(author_payload, "uniqueId")
        if username is None:
            return None

        return TikTokAuthor(
            name=self._extract_item_string(author_payload, "nickname"),
            username=username,
            profile_url=f"https://www.tiktok.com/@{username}",
        )

    def _extract_video_id(self, url: str) -> str | None:
        match = re.search(r"/video/([^/?#]+)/?", url)
        return match.group(1) if match else None

    def _extract_username(self, url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"tiktok\.com/@([^/?#]+)/?", url)
        return match.group(1) if match else None

    def _extract_video_detail_payload(self, html: str) -> dict[str, Any] | None:
        match = re.search(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        if not match:
            return None

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

        default_scope = data.get("__DEFAULT_SCOPE__")
        if not isinstance(default_scope, dict):
            return None

        detail_payload = default_scope.get("webapp.video-detail")
        return detail_payload if isinstance(detail_payload, dict) else None

    def _extract_item_payload(
        self, detail_payload: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if not isinstance(detail_payload, dict):
            return None

        item_info = detail_payload.get("itemInfo")
        if not isinstance(item_info, dict):
            return None

        item_struct = item_info.get("itemStruct")
        return item_struct if isinstance(item_struct, dict) else None

    def _extract_share_meta(
        self, detail_payload: dict[str, Any] | None, key: str
    ) -> str | None:
        if not isinstance(detail_payload, dict):
            return None

        share_meta = detail_payload.get("shareMeta")
        if not isinstance(share_meta, dict):
            return None

        value = share_meta.get(key)
        return value if isinstance(value, str) and value else None

    def _extract_video_field(
        self, item_payload: dict[str, Any] | None, key: str
    ) -> str | None:
        if not isinstance(item_payload, dict):
            return None

        video_payload = item_payload.get("video")
        if not isinstance(video_payload, dict):
            return None

        value = video_payload.get(key)
        return value if isinstance(value, str) and value else None

    def _extract_item_string(
        self, payload: dict[str, Any] | None, key: str
    ) -> str | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get(key)
        return value if isinstance(value, str) and value else None

    def _extract_tiktok_description(
        self, item_payload: dict[str, Any] | None
    ) -> str | None:
        description = self._extract_item_string(item_payload, "desc")
        return description if description else None

    def _extract_duration(self, item_payload: dict[str, Any] | None) -> str | None:
        if not isinstance(item_payload, dict):
            return None

        video_payload = item_payload.get("video")
        if not isinstance(video_payload, dict):
            return None

        duration = video_payload.get("duration")
        if isinstance(duration, int):
            return f"PT{duration}S"
        return None

    def _extract_published_at(
        self, item_payload: dict[str, Any] | None
    ) -> datetime | None:
        create_time = self._extract_item_string(item_payload, "createTime")
        if create_time is None:
            return None

        try:
            return datetime.fromtimestamp(int(create_time), tz=UTC)
        except ValueError:
            return None

    def _build_canonical_url(
        self, item_payload: dict[str, Any] | None, video_id: str | None
    ) -> str | None:
        if video_id is None:
            return None

        if not isinstance(item_payload, dict):
            return None

        author_payload = item_payload.get("author")
        if not isinstance(author_payload, dict):
            return None

        username = self._extract_item_string(author_payload, "uniqueId")
        if username is None:
            return None

        return f"https://www.tiktok.com/@{username}/video/{video_id}"

    def _build_embed_url(self, video_id: str | None) -> str | None:
        if video_id is None:
            return None
        return f"https://www.tiktok.com/embed/{video_id}"
