from datetime import UTC, datetime

from app.services.tiktok import TikTokVideoScraperService

TIKTOK_UNIVERSAL_DATA_HTML = """
<html>
  <head>
    <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">
      {
        "__DEFAULT_SCOPE__": {
          "webapp.video-detail": {
            "shareMeta": {
              "title": "Creator on TikTok",
              "desc": "Creator short video"
            },
            "itemInfo": {
              "itemStruct": {
                "id": "9876543210",
                "desc": "",
                "createTime": "1768157731",
                "video": {
                  "duration": 10,
                  "cover": "https://cdn.example.com/tiktok-thumb.jpg",
                  "playAddr": "https://cdn.example.com/tiktok-video.mp4"
                },
                "author": {
                  "uniqueId": "creator",
                  "nickname": "Creator Name"
                }
              }
            }
          }
        }
      }
    </script>
  </head>
</html>
"""


def build_service() -> TikTokVideoScraperService:
    return TikTokVideoScraperService(http_client=None)  # type: ignore[arg-type]


def test_extract_video_detail_payload_reads_universal_data_script() -> None:
    service = build_service()

    payload = service._extract_video_detail_payload(TIKTOK_UNIVERSAL_DATA_HTML)

    assert payload is not None
    assert payload["shareMeta"]["title"] == "Creator on TikTok"


def test_extract_video_detail_payload_returns_none_for_invalid_html() -> None:
    service = build_service()

    payload = service._extract_video_detail_payload("<html><body>No payload</body></html>")

    assert payload is None


def test_extract_item_payload_and_share_meta_read_nested_tiktok_data() -> None:
    service = build_service()
    detail_payload = service._extract_video_detail_payload(TIKTOK_UNIVERSAL_DATA_HTML)

    item_payload = service._extract_item_payload(detail_payload)

    assert item_payload is not None
    assert item_payload["id"] == "9876543210"
    assert service._extract_share_meta(detail_payload, "title") == "Creator on TikTok"
    assert service._extract_share_meta(detail_payload, "missing") is None


def test_extract_author_prefers_primary_video_author_alternate_name() -> None:
    service = build_service()

    author = service._extract_author(
        {
            "author": {
                "name": "Creator Name",
                "alternateName": "@creator",
                "url": "https://www.tiktok.com/@creator",
            }
        },
        None,
    )

    assert author is not None
    assert author.name == "Creator Name"
    assert author.username == "creator"
    assert str(author.profile_url) == "https://www.tiktok.com/@creator"


def test_extract_author_falls_back_to_item_payload() -> None:
    service = build_service()
    detail_payload = service._extract_video_detail_payload(TIKTOK_UNIVERSAL_DATA_HTML)
    item_payload = service._extract_item_payload(detail_payload)

    author = service._extract_author(None, item_payload)

    assert author is not None
    assert author.name == "Creator Name"
    assert author.username == "creator"
    assert str(author.profile_url) == "https://www.tiktok.com/@creator"


def test_extract_video_field_description_duration_and_post_date_from_item_payload() -> None:
    service = build_service()
    detail_payload = service._extract_video_detail_payload(TIKTOK_UNIVERSAL_DATA_HTML)
    item_payload = service._extract_item_payload(detail_payload)

    assert service._extract_video_field(item_payload, "cover") == (
        "https://cdn.example.com/tiktok-thumb.jpg"
    )
    assert service._extract_tiktok_description(item_payload) is None
    assert service._extract_duration(item_payload) == "PT10S"
    assert service._extract_published_at(item_payload) == datetime(
        2026, 1, 11, 18, 55, 31, tzinfo=UTC
    )


def test_build_canonical_and_embed_urls_from_item_payload() -> None:
    service = build_service()
    detail_payload = service._extract_video_detail_payload(TIKTOK_UNIVERSAL_DATA_HTML)
    item_payload = service._extract_item_payload(detail_payload)

    canonical_url = service._build_canonical_url(item_payload, "9876543210")
    embed_url = service._build_embed_url("9876543210")

    assert canonical_url == "https://www.tiktok.com/@creator/video/9876543210"
    assert embed_url == "https://www.tiktok.com/embed/9876543210"
