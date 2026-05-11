from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.scripts import sync_obsidian as sync_module


class DummySession:
    pass


class DummySessionContext:
    async def __aenter__(self):
        return DummySession()

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def restore_obsidian_path():
    original = settings.obsidian_vault_path
    try:
        yield
    finally:
        settings.obsidian_vault_path = original


@pytest.mark.asyncio
async def test_sync_obsidian_exports_and_marks_rows(monkeypatch, restore_obsidian_path):
    settings.obsidian_vault_path = "C:/tmp/vault"
    monkeypatch.setattr(sync_module, "async_session", lambda: DummySessionContext())

    article_ok = SimpleNamespace(
        id=1,
        title="Backend Article",
        url="https://example.com/a",
        ai_relevance_score=0.9,
        summary="summary",
        published_at=datetime(2026, 1, 1),
    )
    article_fail = SimpleNamespace(
        id=2,
        title="Broken Article",
        url="https://example.com/b",
        ai_relevance_score=0.2,
        summary="summary",
        published_at=None,
    )

    calls = {"exported": [], "failed": []}

    async def fake_list_pending_obsidian_articles_db(limit, db):
        assert limit == 5
        return [(article_ok, "Feed A"), (article_fail, "Feed B")]

    def fake_write_curated_article_to_obsidian(**kwargs):
        if kwargs["article_id"] == 2:
            raise RuntimeError("write failed")
        return "C:/vault/Signal Curated/1-backend-article.md"

    async def fake_mark_exported(article_id, note_path, db):
        calls["exported"].append((article_id, note_path))

    async def fake_mark_failed(article_id, db):
        calls["failed"].append(article_id)

    monkeypatch.setattr(
        sync_module,
        "list_pending_obsidian_articles_db",
        fake_list_pending_obsidian_articles_db,
    )
    monkeypatch.setattr(
        sync_module,
        "write_curated_article_to_obsidian",
        fake_write_curated_article_to_obsidian,
    )
    monkeypatch.setattr(
        sync_module,
        "mark_article_obsidian_exported_db",
        fake_mark_exported,
    )
    monkeypatch.setattr(
        sync_module,
        "mark_article_obsidian_failed_db",
        fake_mark_failed,
    )

    result = await sync_module.sync_obsidian(limit=5)

    assert result == {"exported": 1, "failed": 1}
    assert calls["exported"] == [(1, "C:/vault/Signal Curated/1-backend-article.md")]
    assert calls["failed"] == [2]


@pytest.mark.asyncio
async def test_sync_obsidian_requires_vault_path(monkeypatch, restore_obsidian_path):
    settings.obsidian_vault_path = ""
    with pytest.raises(ValueError):
        await sync_module.sync_obsidian()
