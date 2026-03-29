from urllib.parse import parse_qs, urlparse

import json
import re
from typing import Any

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
    collect_thumbnail_urls,
    extract_open_graph,
    parse_json_ld_blocks,
    pick_primary_object,
    pick_string,
    pick_thumbnail,
    unique_nonempty_strings,
)
from app.services.video_frames import VideoFrameService


class YouTubeShortsScraperService:
    _CONSENT_COOKIES = {
        "CONSENT": "YES+cb.20210328-17-p0.en+FX+667",
        "SOCS": "CAI",
    }
    _CONSENT_COOKIE_HEADER = "; ".join(
        f"{key}={value}" for key, value in _CONSENT_COOKIES.items()
    )

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        frame_service: VideoFrameService | None = None,
    ) -> None:
        self._http_client = http_client
        self._frame_service = frame_service or VideoFrameService()

    async def scrape_short(
        self, payload: YouTubeShortScrapeRequest
    ) -> YouTubeShortScrapeResponse:
        response = await self._fetch_short_page(str(payload.url))

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
        player_response = self._extract_initial_player_response(response.text)
        short_id = self._extract_short_id(str(response.url)) or self._extract_short_id(
            str(payload.url)
        )
        title = (
            open_graph.get("og:title")
            or parser.meta_tags.get("twitter:title")
            or parser.meta_tags.get("title")
            or pick_string(primary_video, "name")
            or self._extract_player_title(player_response)
        )
        description = (
            open_graph.get("og:description")
            or parser.meta_tags.get("twitter:description")
            or parser.meta_tags.get("description")
            or pick_string(primary_video, "description")
            or self._extract_player_description(player_response)
        )
        thumbnail_url = (
            open_graph.get("og:image")
            or parser.meta_tags.get("twitter:image")
            or pick_thumbnail(primary_video)
            or self._extract_player_thumbnail(player_response)
        )
        video_url = (
            open_graph.get("og:video")
            or open_graph.get("og:video:url")
            or pick_string(primary_video, "contentUrl")
        )
        canonical_url = open_graph.get("og:url") or parser.canonical_url
        if canonical_url and "consent.youtube.com" in canonical_url:
            canonical_url = None
        if canonical_url is None and short_id is not None:
            canonical_url = f"https://www.youtube.com/shorts/{short_id}"

        embed_url = pick_string(primary_video, "embedUrl")

        has_any_metadata = any(
            [
                title,
                description,
                thumbnail_url,
                video_url,
                open_graph,
                json_ld_documents,
            ]
        )

        oembed = None
        if not has_any_metadata:
            oembed = await self._fetch_oembed(str(payload.url))
            title = title or self._extract_oembed_string(oembed, "title")
            thumbnail_url = thumbnail_url or self._extract_oembed_string(
                oembed, "thumbnail_url"
            )
            embed_url = self._extract_oembed_embed_url(oembed) or embed_url
            if canonical_url is None and short_id is not None:
                canonical_url = f"https://www.youtube.com/shorts/{short_id}"
            has_any_metadata = any([title, thumbnail_url, embed_url])

        if embed_url is None and short_id is not None:
            embed_url = f"https://www.youtube.com/embed/{short_id}"

        if not has_any_metadata and short_id is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not extract YouTube Short metadata from the response.",
            )

        duration = pick_string(primary_video, "duration") or self._extract_player_duration(
            player_response
        )
        frame_video_url = self._extract_best_video_stream_url(str(payload.url))
        frames = await self._frame_service.extract_frame_captures(
            video_url=frame_video_url or video_url,
            duration=duration,
            storyboard_spec=self._extract_storyboard_spec(response.text),
        )

        return YouTubeShortScrapeResponse(
            requested_url=payload.url,
            resolved_url=str(response.url),
            canonical_url=canonical_url,
            short_id=short_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            preview_image_urls=self._extract_preview_images(
                primary_video,
                player_response,
                open_graph,
                parser.meta_tags,
                oembed,
            ),
            frames=frames,
            video_url=video_url,
            embed_url=embed_url,
            site_name=open_graph.get("og:site_name"),
            channel=self._extract_channel(primary_video, player_response, oembed),
            published_at=pick_string(primary_video, "uploadDate")
            or pick_string(primary_video, "datePublished"),
            duration=duration,
            open_graph=open_graph,
            json_ld=json_ld_documents,
        )

    async def _fetch_short_page(self, url: str) -> httpx.Response:
        headers = {
            "User-Agent": DEFAULT_SCRAPE_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": self._CONSENT_COOKIE_HEADER,
        }

        try:
            response = await self._http_client.get(
                url,
                follow_redirects=True,
                headers=headers,
            )
            if self._is_consent_page(response.url):
                consent_url = self._extract_continue_url(str(response.url)) or url
                response = await self._http_client.get(
                    consent_url,
                    follow_redirects=True,
                    headers=headers,
                )
            return response
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

    async def _fetch_oembed(self, url: str) -> dict[str, object] | None:
        try:
            response = await self._http_client.get(
                "https://www.youtube.com/oembed",
                params={"url": url, "format": "json"},
                follow_redirects=True,
                headers={
                    "User-Agent": DEFAULT_SCRAPE_USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
        except httpx.HTTPError:
            return None
        if response.status_code != status.HTTP_200_OK:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None

    def _is_consent_page(self, url: httpx.URL) -> bool:
        return url.host == "consent.youtube.com"

    def _extract_continue_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        continue_values = query.get("continue")
        if not continue_values:
            return None
        continue_url = continue_values[0]
        return continue_url if continue_url.startswith("http") else None

    def _extract_channel(
        self,
        primary_video: dict[str, object] | None,
        player_response: dict[str, object] | None = None,
        oembed: dict[str, object] | None = None,
    ) -> YouTubeChannel | None:
        if not isinstance(primary_video, dict):
            return self._extract_channel_from_player_response(
                player_response
            ) or self._extract_channel_from_oembed(oembed)

        author_payload = primary_video.get("author")
        if not isinstance(author_payload, dict):
            return self._extract_channel_from_player_response(
                player_response
            ) or self._extract_channel_from_oembed(oembed)

        channel_url = author_payload.get("url")
        channel_url = channel_url if isinstance(channel_url, str) else None

        return YouTubeChannel(
            name=pick_string(author_payload, "name"),
            handle=self._extract_handle(channel_url),
            channel_id=pick_string(author_payload, "identifier")
            or self._extract_channel_id(channel_url),
            channel_url=channel_url,
        )

    def _extract_channel_from_oembed(
        self, oembed: dict[str, object] | None
    ) -> YouTubeChannel | None:
        author_name = self._extract_oembed_string(oembed, "author_name")
        author_url = self._extract_oembed_string(oembed, "author_url")
        if author_name is None and author_url is None:
            return None
        return YouTubeChannel(
            name=author_name,
            handle=self._extract_handle(author_url),
            channel_id=self._extract_channel_id(author_url),
            channel_url=author_url,
        )

    def _extract_initial_player_response(
        self, html: str
    ) -> dict[str, object] | None:
        patterns = (
            r"ytInitialPlayerResponse\s*=\s*(\{.*?\});",
            r'var\s+ytInitialPlayerResponse\s*=\s*(\{.*?\});',
        )
        for pattern in patterns:
            match = re.search(pattern, html, re.S)
            if not match:
                continue
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    def _extract_storyboard_spec(self, html: str) -> str | None:
        match = re.search(
            r'"playerStoryboardSpecRenderer":\{"spec":"([^"]+)"',
            html,
        )
        return match.group(1) if match else None

    def _extract_best_video_stream_url(self, url: str) -> str | None:
        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            return None

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
        }

        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            return None

        if not isinstance(info, dict):
            return None
        return self._select_best_video_format_url(info)

    def _select_best_video_format_url(self, info: dict[str, Any]) -> str | None:
        formats = info.get("formats")
        if not isinstance(formats, list):
            return None

        candidates: list[dict[str, Any]] = []
        for item in formats:
            if not isinstance(item, dict):
                continue
            if item.get("vcodec") in (None, "none"):
                continue
            url = item.get("url")
            if not isinstance(url, str) or not url:
                continue
            candidates.append(item)

        if not candidates:
            return None

        def sort_key(item: dict[str, Any]) -> tuple[int, int, int, int]:
            ext = item.get("ext")
            protocol = item.get("protocol")
            return (
                int(item.get("height") or 0),
                int(item.get("width") or 0),
                int(item.get("fps") or 0),
                int((ext == "mp4") or (protocol == "https")),
            )

        best = max(candidates, key=sort_key)
        url = best.get("url")
        return url if isinstance(url, str) and url else None

    def _extract_player_title(
        self, player_response: dict[str, object] | None
    ) -> str | None:
        video_details = self._extract_player_dict(player_response, "videoDetails")
        return self._extract_dict_string(video_details, "title")

    def _extract_player_description(
        self, player_response: dict[str, object] | None
    ) -> str | None:
        video_details = self._extract_player_dict(player_response, "videoDetails")
        return self._extract_dict_string(video_details, "shortDescription")

    def _extract_player_thumbnail(
        self, player_response: dict[str, object] | None
    ) -> str | None:
        thumbnails = self._extract_player_thumbnail_urls(player_response)
        return thumbnails[-1] if thumbnails else None

    def _extract_player_thumbnail_urls(
        self, player_response: dict[str, object] | None
    ) -> list[str]:
        video_details = self._extract_player_dict(player_response, "videoDetails")
        if not isinstance(video_details, dict):
            return []
        thumbnail = video_details.get("thumbnail")
        if not isinstance(thumbnail, dict):
            return []
        thumbnails = thumbnail.get("thumbnails")
        if not isinstance(thumbnails, list):
            return []
        results: list[str] = []
        for item in thumbnails:
            if isinstance(item, dict):
                url = item.get("url")
                if isinstance(url, str) and url:
                    results.append(url)
        return results

    def _extract_player_duration(
        self, player_response: dict[str, object] | None
    ) -> str | None:
        video_details = self._extract_player_dict(player_response, "videoDetails")
        seconds = self._extract_dict_string(video_details, "lengthSeconds")
        if seconds is None:
            return None
        try:
            return f"PT{int(seconds)}S"
        except ValueError:
            return None

    def _extract_channel_from_player_response(
        self, player_response: dict[str, object] | None
    ) -> YouTubeChannel | None:
        video_details = self._extract_player_dict(player_response, "videoDetails")
        microformat = self._extract_player_dict(player_response, "microformat")
        player_microformat = self._extract_player_dict(
            microformat, "playerMicroformatRenderer"
        )

        name = self._extract_dict_string(video_details, "author")
        channel_id = self._extract_dict_string(video_details, "channelId")
        channel_url = self._extract_dict_string(player_microformat, "ownerProfileUrl")

        if name is None and channel_id is None and channel_url is None:
            return None

        return YouTubeChannel(
            name=name,
            handle=self._extract_handle(channel_url),
            channel_id=channel_id or self._extract_channel_id(channel_url),
            channel_url=channel_url,
        )

    def _extract_player_dict(
        self, payload: dict[str, object] | None, key: str
    ) -> dict[str, object] | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get(key)
        return value if isinstance(value, dict) else None

    def _extract_dict_string(
        self, payload: dict[str, object] | None, key: str
    ) -> str | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get(key)
        return value if isinstance(value, str) and value else None

    def _extract_oembed_string(
        self, payload: dict[str, object] | None, key: str
    ) -> str | None:
        return self._extract_dict_string(payload, key)

    def _extract_oembed_embed_url(
        self, payload: dict[str, object] | None
    ) -> str | None:
        html = self._extract_oembed_string(payload, "html")
        if not html:
            return None
        match = re.search(r'src=(?:"|\\")([^"\\]+)(?:"|\\")', html)
        return match.group(1) if match else None

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

    def _extract_preview_images(
        self,
        primary_video: dict[str, object] | None,
        player_response: dict[str, object] | None,
        open_graph: dict[str, str],
        meta_tags: dict[str, str],
        oembed: dict[str, object] | None,
    ) -> list[str]:
        return unique_nonempty_strings(
            open_graph.get("og:image"),
            meta_tags.get("twitter:image"),
            *collect_thumbnail_urls(primary_video),
            *self._extract_player_thumbnail_urls(player_response),
            self._extract_oembed_string(oembed, "thumbnail_url"),
        )
