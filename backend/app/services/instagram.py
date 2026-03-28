import re

import httpx
from fastapi import HTTPException, status

from app.schemas.instagram import (
    InstagramAuthor,
    InstagramReelScrapeRequest,
    InstagramReelScrapeResponse,
)
from app.services.social_scrape import (
    DEFAULT_SCRAPE_USER_AGENT,
    MetadataHTMLParser,
    collect_thumbnail_urls,
    extract_open_graph,
    parse_json_ld_blocks,
    pick_primary_object,
    pick_string,
    pick_thumbnail,
    unique_nonempty_strings,
)
from app.services.video_frames import VideoFrameService


class InstagramReelScraperService:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        frame_service: VideoFrameService | None = None,
    ) -> None:
        self._http_client = http_client
        self._frame_service = frame_service or VideoFrameService()

    async def scrape_reel(
        self, payload: InstagramReelScrapeRequest
    ) -> InstagramReelScrapeResponse:
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

        parser = MetadataHTMLParser()
        parser.feed(response.text)

        open_graph = extract_open_graph(parser.meta_tags)
        json_ld_documents = parse_json_ld_blocks(parser.json_ld_blocks)
        primary_video = pick_primary_object(json_ld_documents)

        author = self._extract_author(primary_video)
        reel_id = self._extract_reel_id(str(response.url)) or self._extract_reel_id(
            str(payload.url)
        )
        title = (
            open_graph.get("og:title")
            or parser.meta_tags.get("twitter:title")
            or parser.meta_tags.get("title")
            or pick_string(primary_video, "name")
        )
        description = (
            open_graph.get("og:description")
            or parser.meta_tags.get("twitter:description")
            or parser.meta_tags.get("description")
            or pick_string(primary_video, "description")
        )
        thumbnail_url = (
            open_graph.get("og:image")
            or parser.meta_tags.get("twitter:image")
            or pick_thumbnail(primary_video)
        )
        video_url = (
            open_graph.get("og:video")
            or open_graph.get("og:video:url")
            or pick_string(primary_video, "contentUrl")
        )
        canonical_url = open_graph.get("og:url") or parser.canonical_url
        if canonical_url is None and reel_id is not None:
            canonical_url = f"https://www.instagram.com/reel/{reel_id}/"
        embed_url = pick_string(primary_video, "embedUrl")

        has_any_metadata = any(
            [title, description, thumbnail_url, video_url, open_graph, json_ld_documents]
        )

        if not has_any_metadata and reel_id is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not extract Instagram reel metadata from the response.",
            )

        duration = pick_string(primary_video, "duration")
        frames = await self._frame_service.extract_frame_captures(
            video_url=video_url,
            duration=duration,
        )

        return InstagramReelScrapeResponse(
            requested_url=payload.url,
            resolved_url=str(response.url),
            canonical_url=canonical_url,
            reel_id=reel_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            preview_image_urls=unique_nonempty_strings(
                open_graph.get("og:image"),
                parser.meta_tags.get("twitter:image"),
                *collect_thumbnail_urls(primary_video),
            ),
            frames=frames,
            video_url=video_url,
            embed_url=embed_url,
            site_name=open_graph.get("og:site_name"),
            author=author,
            published_at=pick_string(primary_video, "uploadDate"),
            duration=duration,
            open_graph=open_graph,
            json_ld=json_ld_documents,
        )

    def _extract_author(
        self, primary_video: dict[str, object] | None
    ) -> InstagramAuthor | None:
        if not isinstance(primary_video, dict):
            return None

        author_payload = primary_video.get("author")
        if not isinstance(author_payload, dict):
            return None

        profile_url = author_payload.get("url")
        profile_url = profile_url if isinstance(profile_url, str) else None

        return InstagramAuthor(
            name=pick_string(author_payload, "name"),
            username=self._extract_username(profile_url),
            profile_url=profile_url,
        )

    def _extract_reel_id(self, url: str) -> str | None:
        match = re.search(r"/reel/([^/?#]+)/?", url)
        return match.group(1) if match else None

    def _extract_username(self, url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"instagram\.com/([^/?#]+)/?", url)
        return match.group(1) if match else None
