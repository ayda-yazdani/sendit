import json
import re
from html.parser import HTMLParser
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.schemas.instagram import (
    InstagramAuthor,
    InstagramReelScrapeRequest,
    InstagramReelScrapeResponse,
)

INSTAGRAM_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class _InstagramHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_tags: dict[str, str] = {}
        self.json_ld_blocks: list[str] = []
        self._capture_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if tag.lower() == "meta":
            key = attr_map.get("property") or attr_map.get("name")
            content = attr_map.get("content")
            if key and content:
                self.meta_tags[key] = content
            return

        if tag.lower() == "script":
            script_type = attr_map.get("type", "").lower()
            if script_type == "application/ld+json":
                self._capture_json_ld = True
                self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_json_ld:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capture_json_ld:
            block = "".join(self._json_ld_parts).strip()
            if block:
                self.json_ld_blocks.append(block)
            self._capture_json_ld = False
            self._json_ld_parts = []


class InstagramReelScraperService:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def scrape_reel(
        self, payload: InstagramReelScrapeRequest
    ) -> InstagramReelScrapeResponse:
        try:
            response = await self._http_client.get(
                str(payload.url),
                follow_redirects=True,
                headers={
                    "User-Agent": INSTAGRAM_USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Timed out while fetching the Instagram reel.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch the Instagram reel.",
            ) from exc

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instagram reel not found.",
            )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Instagram returned an error while fetching the reel.",
            )

        parser = _InstagramHTMLParser()
        parser.feed(response.text)

        open_graph = {
            key: value
            for key, value in parser.meta_tags.items()
            if key.startswith("og:")
        }
        json_ld_documents = self._parse_json_ld(parser.json_ld_blocks)
        primary_video = self._pick_primary_video_object(json_ld_documents)

        author = self._extract_author(primary_video)
        reel_id = self._extract_reel_id(str(response.url))
        title = open_graph.get("og:title") or self._pick_string(primary_video, "name")
        description = open_graph.get("og:description") or self._pick_string(
            primary_video, "description"
        )
        thumbnail_url = open_graph.get("og:image") or self._pick_thumbnail(
            primary_video
        )
        video_url = (
            open_graph.get("og:video")
            or open_graph.get("og:video:url")
            or self._pick_string(primary_video, "contentUrl")
        )

        if reel_id is None and not any([title, description, thumbnail_url, video_url]):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not extract Instagram reel metadata from the response.",
            )

        return InstagramReelScrapeResponse(
            requested_url=payload.url,
            resolved_url=str(response.url),
            canonical_url=open_graph.get("og:url"),
            reel_id=reel_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            video_url=video_url,
            embed_url=self._pick_string(primary_video, "embedUrl"),
            site_name=open_graph.get("og:site_name"),
            author=author,
            published_at=self._pick_string(primary_video, "uploadDate"),
            duration=self._pick_string(primary_video, "duration"),
            open_graph=open_graph,
            json_ld=json_ld_documents,
        )

    def _parse_json_ld(self, blocks: list[str]) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        for block in blocks:
            try:
                parsed = json.loads(block)
            except json.JSONDecodeError:
                continue

            if isinstance(parsed, dict):
                documents.append(parsed)
            elif isinstance(parsed, list):
                documents.extend(item for item in parsed if isinstance(item, dict))

        return documents

    def _pick_primary_video_object(
        self, json_ld_documents: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        for document in json_ld_documents:
            document_type = document.get("@type")
            if document_type == "VideoObject":
                return document
            if isinstance(document_type, list) and "VideoObject" in document_type:
                return document
        return json_ld_documents[0] if json_ld_documents else None

    def _extract_author(
        self, primary_video: dict[str, Any] | None
    ) -> InstagramAuthor | None:
        if not isinstance(primary_video, dict):
            return None

        author_payload = primary_video.get("author")
        if not isinstance(author_payload, dict):
            return None

        profile_url = author_payload.get("url")
        profile_url = profile_url if isinstance(profile_url, str) else None

        return InstagramAuthor(
            name=self._pick_string(author_payload, "name"),
            username=self._extract_username(profile_url),
            profile_url=profile_url,
        )

    def _pick_thumbnail(self, primary_video: dict[str, Any] | None) -> str | None:
        if not isinstance(primary_video, dict):
            return None

        thumbnail = primary_video.get("thumbnailUrl")
        if isinstance(thumbnail, list):
            for item in thumbnail:
                if isinstance(item, str):
                    return item
            return None
        if isinstance(thumbnail, str):
            return thumbnail
        return None

    def _pick_string(
        self, payload: dict[str, Any] | None, key: str
    ) -> str | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get(key)
        return value if isinstance(value, str) else None

    def _extract_reel_id(self, url: str) -> str | None:
        match = re.search(r"/reel/([^/?#]+)/?", url)
        return match.group(1) if match else None

    def _extract_username(self, url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"instagram\.com/([^/?#]+)/?", url)
        return match.group(1) if match else None
