from app.services.instagram import InstagramReelScraperService


def build_service() -> InstagramReelScraperService:
    return InstagramReelScraperService(http_client=None)  # type: ignore[arg-type]


def test_extract_author_returns_instagram_author_from_primary_video() -> None:
    service = build_service()

    author = service._extract_author(
        {
            "author": {
                "name": "Creator Name",
                "url": "https://www.instagram.com/example_creator/",
            }
        }
    )

    assert author is not None
    assert author.name == "Creator Name"
    assert author.username == "example_creator"
    assert str(author.profile_url) == "https://www.instagram.com/example_creator/"


def test_extract_author_returns_none_without_author_payload() -> None:
    service = build_service()

    author = service._extract_author({"name": "No author"})

    assert author is None


def test_extract_reel_id_and_username_parse_instagram_urls() -> None:
    service = build_service()

    reel_id = service._extract_reel_id("https://www.instagram.com/reel/abc123/?utm=1")
    username = service._extract_username("https://www.instagram.com/example_creator/")

    assert reel_id == "abc123"
    assert username == "example_creator"
