import logging
from datetime import datetime
from typing import Optional

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.articles.models import Article
from app.modules.articles.ai_service import analyze_articles_batch
from app.modules.feeds.models import Feed

logger = logging.getLogger(__name__)


def _parse_date(date_str) -> Optional[datetime]:
    """Parse RFC 2822 date string"""
    if not date_str:
        return None

    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


async def fetch_feed(feed) -> list[dict]:
    """Fetch and parse RSS feed"""
    feed_url = feed.url
    try:
        parsed = feedparser.parse(feed_url)
        entries = []

        for entry in parsed.entries[:20]:
            content_value = entry.get("content")
            entries.append(
                {
                    "title": entry.get("title", "No title"),
                    "url": entry.get("link", ""),
                    "content": content_value[0].get("value", "")
                    if content_value
                    else "",
                    "summary": entry.get("summary", ""),
                    "published_at": _parse_date(entry.get("published")),
                }
            )

        return entries
    except Exception as e:
        logger.error(f"Error fetching {feed_url}: {e}")
        return []


async def fetch_and_review_feeds(session: AsyncSession) -> int:
    """Fetch all active feeds, AI batch score, and save new articles"""
    result = await session.execute(select(Feed).where(Feed.is_active))
    feeds = result.scalars().all()

    if not feeds:
        return 0

    new_articles_count = 0
    curated_count = 0
    pending_articles = []

    for feed in feeds:
        entries = await fetch_feed(feed)

        for entry in entries:
            existing = await session.execute(
                select(Article).where(Article.url == entry["url"])
            )
            if existing.scalar_one_or_none():
                continue

            article = Article(
                feed_id=feed.id,
                title=entry["title"],
                url=entry["url"],
                content=entry["content"],
                summary=entry["summary"],
                published_at=entry["published_at"],
            )
            pending_articles.append(article)
            session.add(article)
            new_articles_count += 1

        feed.last_fetched_at = datetime.now()

    if pending_articles and settings.groq_api_key:
        logger.info(f"AI batch scoring {len(pending_articles)} articles...")
        
        article_data = [
            (a.title, a.summary or "") for a in pending_articles
        ]
        scores = await analyze_articles_batch(article_data)
        
        for article, score in zip(pending_articles, scores):
            article.ai_relevance_score = score
            article.ai_reviewed = True
            if score >= settings.ai_relevance_threshold:
                article.is_curated = True
                curated_count += 1

    await session.commit()

    return new_articles_count


async def create_feed_db(name: str, url: str, category: str, db: AsyncSession):
    """Create a new feed"""
    feed = Feed(name=name, url=url, category=category, is_active=True)
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return {"id": feed.id, "name": feed.name, "url": feed.url}


async def list_feeds_db(db: AsyncSession):
    """List all feeds"""
    result = await db.execute(select(Feed))
    feeds = result.scalars().all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "url": f.url,
            "category": f.category,
            "is_active": f.is_active,
        }
        for f in feeds
    ]
