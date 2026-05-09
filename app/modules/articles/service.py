from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.articles.models import Article
from app.modules.feeds.models import Feed


async def list_articles_db(limit: int, db: AsyncSession, curated: bool = False):
    """List fetched articles. Filter by curated=True for AI-approved only."""
    query = select(Article)

    if curated:
        query = query.where(Article.is_curated)

    query = query.order_by(Article.fetched_at.desc()).limit(limit)

    result = await db.execute(query)
    articles = result.scalars().all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "url": a.url,
            "fetched_at": a.fetched_at.isoformat() if a.fetched_at else None,
            "is_curated": a.is_curated,
            "is_rejected": a.is_rejected,
            "ai_score": a.ai_relevance_score,
        }
        for a in articles
    ]


async def list_pending_obsidian_articles_db(limit: int, db: AsyncSession):
    """List curated articles pending Obsidian export."""
    result = await db.execute(
        select(Article, Feed.name)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Article.is_curated.is_(True))
        .where(Article.obsidian_export_status == "pending")
        .order_by(Article.ai_relevance_score.desc(), Article.fetched_at.desc())
        .limit(limit)
    )
    return result.all()


async def mark_article_obsidian_exported_db(
    article_id: int, note_path: str, db: AsyncSession
) -> None:
    article = await db.get(Article, article_id)
    if not article:
        return
    article.obsidian_export_status = "exported"
    article.obsidian_exported_at = datetime.now()
    article.obsidian_note_path = note_path
    await db.commit()


async def mark_article_obsidian_failed_db(
    article_id: int, db: AsyncSession, keep_pending: bool = False
) -> None:
    article = await db.get(Article, article_id)
    if not article:
        return
    article.obsidian_export_status = "pending" if keep_pending else "failed"
    article.obsidian_note_path = None
    await db.commit()
