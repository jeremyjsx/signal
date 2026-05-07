from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.articles.models import Article


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
