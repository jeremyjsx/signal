import pytest

from app.modules.feeds import scheduler as scheduler_module


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class FakeSession:
    def __init__(self, lock_acquired=True):
        self.lock_acquired = lock_acquired
        self.added = []
        self.commit_count = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, obj):
        return None

    async def execute(self, stmt, params=None):
        stmt_text = str(stmt)
        if "pg_try_advisory_lock" in stmt_text:
            return FakeScalarResult(self.lock_acquired)
        return FakeScalarResult(None)


class FakeSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_fetch_all_feeds_job_records_success(monkeypatch):
    session = FakeSession(lock_acquired=True)
    monkeypatch.setattr(
        scheduler_module, "async_session", lambda: FakeSessionContext(session)
    )

    async def fake_fetch_and_review_feeds(_session):
        return 7

    monkeypatch.setattr(
        scheduler_module, "fetch_and_review_feeds", fake_fetch_and_review_feeds
    )

    await scheduler_module.fetch_all_feeds_job()

    run = session.added[0]
    assert run.job_name == "fetch_feeds"
    assert run.status == "success"
    assert run.new_articles == 7
    assert run.duration_ms is not None


@pytest.mark.asyncio
async def test_cleanup_old_articles_job_records_skipped_when_lock_unavailable(monkeypatch):
    session = FakeSession(lock_acquired=False)
    monkeypatch.setattr(
        scheduler_module, "async_session", lambda: FakeSessionContext(session)
    )

    called = {"cleanup": False}

    async def fake_cleanup_old_articles(_session):
        called["cleanup"] = True
        return {"deleted_articles": 1, "retention_days": 30}

    monkeypatch.setattr(scheduler_module, "cleanup_old_articles", fake_cleanup_old_articles)

    await scheduler_module.cleanup_old_articles_job()

    run = session.added[0]
    assert run.job_name == "cleanup_old_articles"
    assert run.status == "skipped"
    assert "another instance" in (run.message or "")
    assert called["cleanup"] is False
