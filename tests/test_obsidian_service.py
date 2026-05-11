from pathlib import Path

import pytest

from app.core.config import settings
from app.modules.articles.obsidian_service import write_curated_article_to_obsidian


@pytest.fixture
def restore_obsidian_path():
    original = settings.obsidian_vault_path
    try:
        yield
    finally:
        settings.obsidian_vault_path = original


def test_write_curated_article_requires_vault_path(restore_obsidian_path):
    settings.obsidian_vault_path = ""
    with pytest.raises(ValueError):
        write_curated_article_to_obsidian(
            article_id=1,
            title="Test",
            url="https://example.com",
            score=0.8,
            summary="summary",
            published_at=None,
            feed_name="Feed",
        )


def test_write_curated_article_creates_markdown_file(tmp_path, restore_obsidian_path):
    settings.obsidian_vault_path = str(tmp_path)
    path = write_curated_article_to_obsidian(
        article_id=10,
        title="PostgreSQL Indexing Basics",
        url="https://example.com/pg",
        score=0.91,
        summary="A good article",
        published_at="2026-05-10T12:00:00",
        feed_name="Planet PostgreSQL",
    )
    note_path = Path(path)
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "# PostgreSQL Indexing Basics" in content
    assert "- AI Score: 0.91" in content
    assert "A good article" in content


def test_write_curated_article_is_idempotent(tmp_path, restore_obsidian_path):
    settings.obsidian_vault_path = str(tmp_path)
    first_path = write_curated_article_to_obsidian(
        article_id=20,
        title="Reliable Queues in Go",
        url="https://example.com/go",
        score=0.88,
        summary="first",
        published_at=None,
        feed_name="Go Blog",
    )
    note_path = Path(first_path)
    note_path.write_text("manual edit", encoding="utf-8")

    second_path = write_curated_article_to_obsidian(
        article_id=20,
        title="Reliable Queues in Go",
        url="https://example.com/go",
        score=0.75,
        summary="second",
        published_at=None,
        feed_name="Go Blog",
    )

    assert first_path == second_path
    assert note_path.read_text(encoding="utf-8") == "manual edit"
