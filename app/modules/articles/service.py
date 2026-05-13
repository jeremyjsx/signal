from datetime import datetime
from typing import Optional

from sqlalchemy import asc, desc, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.articles.models import Article, ArticleScore, ArticleTag
from app.modules.feeds.models import Feed


async def list_articles_db(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    curated: Optional[bool] = None,
    export_status: Optional[str] = None,
    score_min: Optional[float] = None,
    tag: Optional[str] = None,
    order_by: str = "fetched_at",
    order_dir: str = "desc",
):
    """List fetched articles with pagination, filtering and ordering."""
    score_subquery = (
        select(func.max(ArticleScore.final_score))
        .where(ArticleScore.article_id == Article.id)
        .scalar_subquery()
    )
    query = (
        select(Article, score_subquery.label("final_score"), Feed.name)
        .join(Feed, Feed.id == Article.feed_id)
    )
    count_query = select(func.count(Article.id))

    if curated is not None:
        query = query.where(Article.is_curated.is_(curated))
        count_query = count_query.where(Article.is_curated.is_(curated))

    if export_status:
        query = query.where(Article.obsidian_export_status == export_status)
        count_query = count_query.where(Article.obsidian_export_status == export_status)

    if score_min is not None:
        query = query.where(score_subquery >= score_min)
        count_query = count_query.where(score_subquery >= score_min)

    if tag:
        tag_exists = exists(
            select(1).where(
                ArticleTag.article_id == Article.id,
                ArticleTag.tag == tag.lower(),
            )
        )
        query = query.where(tag_exists)
        count_query = count_query.where(tag_exists)

    order_dir = order_dir.lower()
    order_by = order_by.lower()
    if order_by == "score":
        order_column = score_subquery
    else:
        order_column = Article.fetched_at
    order_function = desc if order_dir == "desc" else asc
    query = query.order_by(order_function(order_column))
    query = query.offset(offset).limit(limit)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0
    result = await db.execute(query)
    rows = result.all()
    return {
        "items": [
            {
                "id": article.id,
                "title": article.title,
                "url": article.url,
                "fetched_at": (
                    article.fetched_at.isoformat() if article.fetched_at else None
                ),
                "is_curated": article.is_curated,
                "is_rejected": article.is_rejected,
                "ai_score": article.ai_relevance_score,
                "score": score,
                "feed_name": feed_name,
                "obsidian_export_status": article.obsidian_export_status,
            }
            for article, score, feed_name in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


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


async def retry_failed_obsidian_exports_db(limit: int, db: AsyncSession) -> dict:
    """Move failed Obsidian exports back to pending for retry."""
    result = await db.execute(
        select(Article)
        .where(Article.obsidian_export_status == "failed")
        .order_by(Article.fetched_at.desc())
        .limit(limit)
    )
    failed_articles = result.scalars().all()
    for article in failed_articles:
        article.obsidian_export_status = "pending"
        article.obsidian_note_path = None

    await db.commit()
    return {
        "retried": len(failed_articles),
        "article_ids": [article.id for article in failed_articles],
    }
