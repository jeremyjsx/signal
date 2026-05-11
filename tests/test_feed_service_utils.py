from app.modules.feeds.service import _extract_rule_tags, _normalize_url, _url_hash


def test_normalize_url_removes_tracking_params_and_fragment():
    raw_url = (
        "HTTPS://Example.COM/path/to/article/?utm_source=twitter&x=1&fbclid=abc#section"
    )
    normalized = _normalize_url(raw_url)
    assert normalized == "https://example.com/path/to/article?x=1"


def test_url_hash_is_stable_for_equivalent_urls():
    url_a = "https://example.com/post/?utm_campaign=abc&id=42"
    url_b = "https://example.com/post?id=42"
    assert _url_hash(url_a) == _url_hash(url_b)


def test_extract_rule_tags_uses_category_and_keywords():
    tags = _extract_rule_tags(
        title="FastAPI with Redis for low latency APIs",
        summary="Using AWS and Postgres in backend architecture",
        category="Backend",
    )
    assert "backend" in tags
    assert "python-backend" in tags
    assert "caching" in tags
    assert "cloud" in tags
    assert "postgresql" in tags
    assert "performance" in tags
