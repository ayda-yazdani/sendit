import json
from html.parser import HTMLParser
from typing import Any


DEFAULT_SCRAPE_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class MetadataHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_tags: dict[str, str] = {}
        self.json_ld_blocks: list[str] = []
        self.canonical_url: str | None = None
        self._capture_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        normalized_tag = tag.lower()

        if normalized_tag == "meta":
            key = attr_map.get("property") or attr_map.get("name")
            content = attr_map.get("content")
            if key and content:
                self.meta_tags[key] = content
            return

        if normalized_tag == "link":
            rel = attr_map.get("rel", "").lower().split()
            href = attr_map.get("href")
            if "canonical" in rel and href and self.canonical_url is None:
                self.canonical_url = href
            return

        if normalized_tag == "script":
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


def extract_open_graph(meta_tags: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in meta_tags.items() if key.startswith("og:")}


def parse_json_ld_blocks(blocks: list[str]) -> list[dict[str, Any]]:
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


def pick_primary_object(
    json_ld_documents: list[dict[str, Any]],
    preferred_types: tuple[str, ...] = ("VideoObject",),
) -> dict[str, Any] | None:
    for document in json_ld_documents:
        document_type = document.get("@type")
        if isinstance(document_type, str) and document_type in preferred_types:
            return document
        if isinstance(document_type, list) and any(
            preferred_type in document_type for preferred_type in preferred_types
        ):
            return document
    return json_ld_documents[0] if json_ld_documents else None


def pick_string(payload: dict[str, Any] | None, key: str) -> str | None:
    if not isinstance(payload, dict):
        return None

    value = payload.get(key)
    return value if isinstance(value, str) else None


def pick_thumbnail(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None

    thumbnail = payload.get("thumbnailUrl")
    if isinstance(thumbnail, list):
        for item in thumbnail:
            if isinstance(item, str):
                return item
        return None

    if isinstance(thumbnail, str):
        return thumbnail

    return None
