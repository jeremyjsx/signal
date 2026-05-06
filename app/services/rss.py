import logging
from datetime import datetime, timezone
from typing import Optional

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.feed import Feed

logger = logging.getLogger(__name__)


async def fetch_feed(feed: Feed) -> list[dict]:
    """Fetch and parse RSS feed, return list of entries"""
    try:
        parsed = feedparser.parse(feed.url)
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
        logger.error(f"Error fetching {feed.url}: {e}")
        return []


def _parse_date(date_str) -> Optional[datetime]:
    """Parse RFC 2822 date string"""
    if not date_str:
        return None

    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(date_str)
    except Exception:
        return None


async def fetch_all_feeds(session: AsyncSession) -> int:
    """Fetch all active feeds and save new articles"""
    result = await session.execute(select(Feed).where(Feed.is_active))
    feeds = result.scalars().all()

    if not feeds:
        return 0

    new_articles_count = 0

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
            session.add(article)
            new_articles_count += 1

        feed.last_fetched_at = datetime.now(timezone.utc)
    await session.commit()

    return new_articles_count
