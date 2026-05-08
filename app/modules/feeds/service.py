import logging
from datetime import datetime
from typing import Optional

import feedparser
import httpx
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.core.config import settings
from app.modules.articles.models import Article
from app.modules.articles.ai_service import analyze_articles_batch
from app.modules.articles.obsidian_service import write_curated_article_to_obsidian
from app.modules.feeds.models import Feed, JobRun

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
        parsed = feedparser.parse(await _fetch_feed_content(feed_url))
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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=8),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)
async def _fetch_feed_content(url: str) -> str:
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def fetch_and_review_feeds(session: AsyncSession) -> int:
    """Fetch all active feeds, AI batch score, and upsert new articles."""
    result = await session.execute(select(Feed).where(Feed.is_active))
    feeds = result.scalars().all()

    if not feeds:
        return 0

    new_articles_count = 0
    for feed in feeds:
        entries = await fetch_feed(feed)
        rows_to_insert = []

        for entry in entries:
            url = entry["url"]
            if not url:
                continue

            rows_to_insert.append(
                {
                    "feed_id": feed.id,
                    "title": entry["title"],
                    "url": url,
                    "content": entry["content"],
                    "summary": entry["summary"],
                    "published_at": entry["published_at"],
                }
            )

        if rows_to_insert:
            insert_stmt = (
                insert(Article)
                .values(rows_to_insert)
                .on_conflict_do_nothing(index_elements=[Article.url])
                .returning(
                    Article.id,
                    Article.title,
                    Article.summary,
                    Article.url,
                    Article.published_at,
                )
            )
            inserted_rows = (await session.execute(insert_stmt)).all()
            new_articles_count += len(inserted_rows)

            if inserted_rows and settings.groq_api_key:
                logger.info(f"AI batch scoring {len(inserted_rows)} articles...")
                article_data = [(row.title, row.summary or "") for row in inserted_rows]
                scores = await analyze_articles_batch(article_data)

                for row, score in zip(inserted_rows, scores):
                    is_curated = score >= settings.ai_relevance_threshold
                    await session.execute(
                        update(Article)
                        .where(Article.id == row.id)
                        .values(
                            ai_relevance_score=score,
                            ai_reviewed=True,
                            is_curated=is_curated,
                            obsidian_export_status="pending" if is_curated else None,
                        )
                    )
                    if is_curated:
                        write_curated_article_to_obsidian(
                            article_id=row.id,
                            title=row.title,
                            url=row.url,
                            score=score,
                            summary=row.summary,
                            published_at=(
                                row.published_at.isoformat()
                                if row.published_at
                                else None
                            ),
                            feed_name=feed.name,
                        )

        feed.last_fetched_at = datetime.now()

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


async def list_job_runs_db(limit: int, db: AsyncSession):
    """List latest scheduler job runs."""
    result = await db.execute(
        select(JobRun).order_by(JobRun.started_at.desc()).limit(limit)
    )
    runs = result.scalars().all()
    return [
        {
            "id": run.id,
            "job_name": run.job_name,
            "status": run.status,
            "new_articles": run.new_articles,
            "message": run.message,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration_ms": run.duration_ms,
        }
        for run in runs
    ]
