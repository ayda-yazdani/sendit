import re

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

        video_id = self._extract_video_id(str(response.url))
        title = open_graph.get("og:title") or pick_string(primary_video, "name")
        description = open_graph.get("og:description") or pick_string(
            primary_video, "description"
        )
        thumbnail_url = open_graph.get("og:image") or pick_thumbnail(primary_video)
        video_url = (
            open_graph.get("og:video")
            or open_graph.get("og:video:url")
            or pick_string(primary_video, "contentUrl")
        )

        if video_id is None and not any([title, description, thumbnail_url, video_url]):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not extract TikTok video metadata from the response.",
            )

        return TikTokVideoScrapeResponse(
            requested_url=payload.url,
            resolved_url=str(response.url),
            canonical_url=open_graph.get("og:url") or parser.canonical_url,
            video_id=video_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            video_url=video_url,
            embed_url=pick_string(primary_video, "embedUrl"),
            site_name=open_graph.get("og:site_name"),
            author=self._extract_author(primary_video),
            published_at=pick_string(primary_video, "uploadDate")
            or pick_string(primary_video, "datePublished"),
            duration=pick_string(primary_video, "duration"),
            open_graph=open_graph,
            json_ld=json_ld_documents,
        )

    def _extract_author(
        self, primary_video: dict[str, object] | None
    ) -> TikTokAuthor | None:
        if not isinstance(primary_video, dict):
            return None

        author_payload = primary_video.get("author")
        if not isinstance(author_payload, dict):
            return None

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

    def _extract_video_id(self, url: str) -> str | None:
        match = re.search(r"/video/([^/?#]+)/?", url)
        return match.group(1) if match else None

    def _extract_username(self, url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"tiktok\.com/@([^/?#]+)/?", url)
        return match.group(1) if match else None
