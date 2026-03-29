from app.services.youtube import YouTubeShortsScraperService


def build_service() -> YouTubeShortsScraperService:
    return YouTubeShortsScraperService(http_client=None)  # type: ignore[arg-type]


def test_extract_channel_returns_handle_and_identifier_from_author_payload() -> None:
    service = build_service()

    channel = service._extract_channel(
        {
            "author": {
                "name": "Shorts Creator",
                "url": "https://www.youtube.com/@shortscreator",
                "identifier": "UC123456789",
            }
        }
    )

    assert channel is not None
    assert channel.name == "Shorts Creator"
    assert channel.handle == "shortscreator"
    assert channel.channel_id == "UC123456789"
    assert str(channel.channel_url) == "https://www.youtube.com/@shortscreator"


def test_extract_channel_falls_back_to_channel_id_from_url() -> None:
    service = build_service()

    channel = service._extract_channel(
        {
            "author": {
                "name": "Shorts Creator",
                "url": "https://www.youtube.com/channel/UC999999999",
            }
        }
    )

    assert channel is not None
    assert channel.handle is None
    assert channel.channel_id == "UC999999999"


def test_extract_short_id_handle_and_channel_id_parse_youtube_urls() -> None:
    service = build_service()

    short_id = service._extract_short_id("https://www.youtube.com/shorts/xyz987?feature=share")
    handle = service._extract_handle("https://www.youtube.com/@shortscreator")
    channel_id = service._extract_channel_id(
        "https://www.youtube.com/channel/UC123456789/videos"
    )

    assert short_id == "xyz987"
    assert handle == "shortscreator"
    assert channel_id == "UC123456789"


def test_select_best_video_format_url_prefers_highest_resolution_video_stream() -> None:
    service = build_service()

    url = service._select_best_video_format_url(
        {
            "formats": [
                {
                    "format_id": "251",
                    "url": "https://example.com/audio.webm",
                    "vcodec": "none",
                    "acodec": "opus",
                },
                {
                    "format_id": "298",
                    "url": "https://example.com/video-720.mp4",
                    "vcodec": "avc1.4d4020",
                    "height": 1280,
                    "width": 720,
                    "fps": 45,
                    "ext": "mp4",
                    "protocol": "https",
                },
                {
                    "format_id": "399",
                    "url": "https://example.com/video-1080.mp4",
                    "vcodec": "av01.0.09M.08",
                    "height": 1920,
                    "width": 1080,
                    "fps": 45,
                    "ext": "mp4",
                    "protocol": "https",
                },
            ]
        }
    )

    assert url == "https://example.com/video-1080.mp4"
