from app.services.social_scrape import (
    MetadataHTMLParser,
    extract_open_graph,
    parse_json_ld_blocks,
    pick_primary_object,
    pick_string,
    pick_thumbnail,
)

HTML = """
<html>
  <head>
    <meta property="og:title" content="Example title" />
    <meta name="description" content="Example description" />
    <meta property="og:image" content="https://cdn.example.com/image.jpg" />
    <link rel="canonical prefetch" href="https://example.com/post/123" />
    <script type="application/ld+json">
      {"@type": "Article", "name": "Example article"}
    </script>
    <script type="application/ld+json">
      [{"@type": "VideoObject", "name": "Example video"}]
    </script>
  </head>
</html>
"""


def test_metadata_html_parser_extracts_meta_tags_canonical_url_and_json_ld() -> None:
    parser = MetadataHTMLParser()
    parser.feed(HTML)

    assert parser.meta_tags["og:title"] == "Example title"
    assert parser.meta_tags["description"] == "Example description"
    assert parser.canonical_url == "https://example.com/post/123"
    assert len(parser.json_ld_blocks) == 2


def test_extract_open_graph_filters_meta_tags() -> None:
    result = extract_open_graph(
        {
            "og:title": "Example title",
            "og:image": "https://cdn.example.com/image.jpg",
            "description": "Ignore me",
        }
    )

    assert result == {
        "og:title": "Example title",
        "og:image": "https://cdn.example.com/image.jpg",
    }


def test_parse_json_ld_blocks_skips_invalid_json_and_flattens_lists() -> None:
    result = parse_json_ld_blocks(
        [
            '{"@type":"Article","name":"Example article"}',
            '[{"@type":"VideoObject","name":"Example video"}]',
            'not-json',
        ]
    )

    assert result == [
        {"@type": "Article", "name": "Example article"},
        {"@type": "VideoObject", "name": "Example video"},
    ]


def test_pick_primary_object_prefers_requested_type_and_falls_back() -> None:
    documents = [
        {"@type": "Article", "name": "Article first"},
        {"@type": ["Thing", "VideoObject"], "name": "Preferred video"},
    ]

    preferred = pick_primary_object(documents)
    fallback = pick_primary_object([{"@type": "Article", "name": "Article first"}])

    assert preferred == {"@type": ["Thing", "VideoObject"], "name": "Preferred video"}
    assert fallback == {"@type": "Article", "name": "Article first"}


def test_pick_string_returns_only_strings() -> None:
    assert pick_string({"name": "Example"}, "name") == "Example"
    assert pick_string({"name": 123}, "name") is None
    assert pick_string(None, "name") is None


def test_pick_thumbnail_supports_strings_and_lists() -> None:
    assert pick_thumbnail({"thumbnailUrl": "https://cdn.example.com/image.jpg"}) == (
        "https://cdn.example.com/image.jpg"
    )
    assert pick_thumbnail(
        {"thumbnailUrl": [123, "https://cdn.example.com/list-image.jpg"]}
    ) == "https://cdn.example.com/list-image.jpg"
    assert pick_thumbnail({"thumbnailUrl": [123]}) is None
    assert pick_thumbnail(None) is None
