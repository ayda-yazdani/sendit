import re

import httpx
from fastapi import HTTPException, status

from app.schemas.youtube import (
    YouTubeChannel,
    YouTubeShortScrapeRequest,
    YouTubeShortScrapeResponse,
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


class YouTubeShortsScraperService:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def scrape_short(
        self, payload: YouTubeShortScrapeRequest
    ) -> YouTubeShortScrapeResponse:
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
                detail="Timed out while fetching the YouTube Short.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch the YouTube Short.",
            ) from exc

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="YouTube Short not found.",
            )

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="YouTube returned an error while fetching the Short.",
            )

        parser = MetadataHTMLParser()
        parser.feed(response.text)

        open_graph = extract_open_graph(parser.meta_tags)
        json_ld_documents = parse_json_ld_blocks(parser.json_ld_blocks)
        primary_video = pick_primary_object(json_ld_documents)

        short_id = self._extract_short_id(str(response.url))
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

        if not any(
            [title, description, thumbnail_url, video_url, open_graph, json_ld_documents]
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not extract YouTube Short metadata from the response.",
            )

        embed_url = pick_string(primary_video, "embedUrl")
        if embed_url is None and short_id is not None:
            embed_url = f"https://www.youtube.com/embed/{short_id}"

        return YouTubeShortScrapeResponse(
            requested_url=payload.url,
            resolved_url=str(response.url),
            canonical_url=open_graph.get("og:url") or parser.canonical_url,
            short_id=short_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            video_url=video_url,
            embed_url=embed_url,
            site_name=open_graph.get("og:site_name"),
            channel=self._extract_channel(primary_video),
            published_at=pick_string(primary_video, "uploadDate")
            or pick_string(primary_video, "datePublished"),
            duration=pick_string(primary_video, "duration"),
            open_graph=open_graph,
            json_ld=json_ld_documents,
        )

    def _extract_channel(
        self, primary_video: dict[str, object] | None
    ) -> YouTubeChannel | None:
        if not isinstance(primary_video, dict):
            return None

        author_payload = primary_video.get("author")
        if not isinstance(author_payload, dict):
            return None

        channel_url = author_payload.get("url")
        channel_url = channel_url if isinstance(channel_url, str) else None

        return YouTubeChannel(
            name=pick_string(author_payload, "name"),
            handle=self._extract_handle(channel_url),
            channel_id=pick_string(author_payload, "identifier")
            or self._extract_channel_id(channel_url),
            channel_url=channel_url,
        )

    def _extract_short_id(self, url: str) -> str | None:
        match = re.search(r"/shorts/([^/?#]+)/?", url)
        return match.group(1) if match else None

    def _extract_handle(self, url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"youtube\.com/@([^/?#]+)/?", url)
        return match.group(1) if match else None

    def _extract_channel_id(self, url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"youtube\.com/channel/([^/?#]+)/?", url)
        return match.group(1) if match else None
