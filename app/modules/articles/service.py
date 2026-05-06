from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.articles.models import Article


async def list_articles_db(limit: int, db: AsyncSession):
    """List fetched articles"""
    result = await db.execute(
        select(Article).order_by(Article.fetched_at.desc()).limit(limit)
    )
    articles = result.scalars().all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "url": a.url,
            "fetched_at": a.fetched_at.isoformat() if a.fetched_at else None,
            "is_curated": a.is_curated,
            "is_rejected": a.is_rejected,
        }
        for a in articles
    ]
