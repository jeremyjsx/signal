from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.modules.feeds import service as feed_service


@pytest.fixture
def restore_feed_disable_threshold():
    original = settings.feed_disable_after_failures
    try:
        yield
    finally:
        settings.feed_disable_after_failures = original


def test_mark_feed_fetch_failure_increments_and_disables_at_threshold(
    restore_feed_disable_threshold,
):
    settings.feed_disable_after_failures = 3
    feed = SimpleNamespace(
        consecutive_failures=2,
        last_error_at=None,
        last_error_message=None,
        is_active=True,
        auto_disabled_at=None,
    )

    feed_service._mark_feed_fetch_failure(feed, "network timeout")

    assert feed.consecutive_failures == 3
    assert feed.last_error_at is not None
    assert feed.last_error_message == "network timeout"
    assert feed.is_active is False
    assert feed.auto_disabled_at is not None


def test_mark_feed_fetch_success_resets_failure_state():
    feed = SimpleNamespace(
        consecutive_failures=5,
        last_fetched_at=None,
        last_success_at=None,
        last_error_at=datetime.now(),
        last_error_message="boom",
    )

    feed_service._mark_feed_fetch_success(feed)

    assert feed.consecutive_failures == 0
    assert feed.last_fetched_at is not None
    assert feed.last_success_at is not None
    assert feed.last_error_at is None
    assert feed.last_error_message is None


class FakeDb:
    def __init__(self, feed=None):
        self.feed = feed
        self.committed = False
        self.refreshed = False

    async def get(self, model, feed_id):
        return self.feed

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed = True


@pytest.mark.asyncio
async def test_reactivate_feed_db_resets_health_fields():
    feed = SimpleNamespace(
        id=7,
        name="Test Feed",
        is_active=False,
        consecutive_failures=4,
        last_error_at=datetime.now(),
        last_error_message="bad response",
        auto_disabled_at=datetime.now(),
    )
    db = FakeDb(feed=feed)

    result = await feed_service.reactivate_feed_db(feed_id=7, db=db)

    assert result["id"] == 7
    assert result["is_active"] is True
    assert result["consecutive_failures"] == 0
    assert feed.last_error_at is None
    assert feed.last_error_message is None
    assert feed.auto_disabled_at is None
    assert db.committed is True
    assert db.refreshed is True


@pytest.mark.asyncio
async def test_reactivate_feed_db_not_found_returns_error():
    db = FakeDb(feed=None)
    result = await feed_service.reactivate_feed_db(feed_id=99, db=db)
    assert result == {"error": "Feed not found"}
    assert db.committed is False


class FakeDeleteResult:
    def __init__(self, rowcount):
        self.rowcount = rowcount


class FakeCleanupDb:
    def __init__(self, rowcount):
        self.rowcount = rowcount
        self.committed = False
        self.last_stmt = None

    async def execute(self, stmt):
        self.last_stmt = stmt
        return FakeDeleteResult(self.rowcount)

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_cleanup_old_articles_returns_deleted_count_and_commits():
    db = FakeCleanupDb(rowcount=12)
    result = await feed_service.cleanup_old_articles(db)

    assert result["deleted_articles"] == 12
    assert result["retention_days"] == settings.non_curated_retention_days
    assert "cutoff" in result
    assert db.committed is True
    assert db.last_stmt is not None
