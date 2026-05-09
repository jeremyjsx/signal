import asyncio
import logging

from app.core.config import settings
from app.core.database import async_session
from app.modules.articles.obsidian_service import write_curated_article_to_obsidian
from app.modules.articles.service import (
    list_pending_obsidian_articles_db,
    mark_article_obsidian_exported_db,
    mark_article_obsidian_failed_db,
)

logger = logging.getLogger(__name__)


async def sync_obsidian(limit: int = 20) -> dict:
    if not settings.obsidian_vault_path.strip():
        raise ValueError("OBSIDIAN_VAULT_PATH is required for local sync.")

    exported = 0
    failed = 0

    async with async_session() as db:
        pending_rows = await list_pending_obsidian_articles_db(limit=limit, db=db)
        for article, feed_name in pending_rows:
            try:
                note_path = write_curated_article_to_obsidian(
                    article_id=article.id,
                    title=article.title,
                    url=article.url,
                    score=article.ai_relevance_score or 0.0,
                    summary=article.summary,
                    published_at=(
                        article.published_at.isoformat()
                        if article.published_at
                        else None
                    ),
                    feed_name=feed_name,
                )
                await mark_article_obsidian_exported_db(
                    article_id=article.id, note_path=note_path, db=db
                )
                exported += 1
            except Exception:
                logger.exception(
                    "Failed exporting article %s to Obsidian", article.id
                )
                await mark_article_obsidian_failed_db(article_id=article.id, db=db)
                failed += 1

    return {"exported": exported, "failed": failed}


def main() -> None:
    result = asyncio.run(sync_obsidian())
    print(
        f"Obsidian sync completed: exported={result['exported']}, failed={result['failed']}"
    )


if __name__ == "__main__":
    main()
