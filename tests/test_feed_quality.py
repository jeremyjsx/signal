from app.modules.feeds.service import _classify_feed_quality


def test_classify_feed_quality_disabled_when_inactive():
    status = _classify_feed_quality(
        is_active=False,
        consecutive_failures=0,
        total_scored=100,
        curated_rate=0.5,
        min_scored_articles=10,
        min_curated_rate=0.1,
    )
    assert status == "disabled"


def test_classify_feed_quality_degraded_with_consecutive_failures():
    status = _classify_feed_quality(
        is_active=True,
        consecutive_failures=2,
        total_scored=100,
        curated_rate=0.5,
        min_scored_articles=10,
        min_curated_rate=0.1,
    )
    assert status == "degraded"


def test_classify_feed_quality_degraded_with_low_curated_rate():
    status = _classify_feed_quality(
        is_active=True,
        consecutive_failures=0,
        total_scored=20,
        curated_rate=0.05,
        min_scored_articles=10,
        min_curated_rate=0.1,
    )
    assert status == "degraded"


def test_classify_feed_quality_healthy_when_above_threshold():
    status = _classify_feed_quality(
        is_active=True,
        consecutive_failures=0,
        total_scored=20,
        curated_rate=0.2,
        min_scored_articles=10,
        min_curated_rate=0.1,
    )
    assert status == "healthy"
