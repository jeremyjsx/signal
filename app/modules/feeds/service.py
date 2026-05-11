import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.core.config import settings
from app.modules.articles.models import Article, ArticleDecision, ArticleScore, ArticleTag
from app.modules.articles.ai_service import analyze_articles_batch
from app.modules.feeds.models import Feed, JobRun

logger = logging.getLogger(__name__)
AI_MODEL_NAME = "llama-3.1-8b-instant"

IGNORED_TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}

RULE_TAG_KEYWORDS = {
    "postgres": "postgresql",
    "sql": "databases",
    "redis": "caching",
    "kafka": "messaging",
    "rabbitmq": "messaging",
    "queue": "messaging",
    "python": "python-backend",
    "fastapi": "python-backend",
    "go": "go-backend",
    "golang": "go-backend",
    "javascript": "javascript-backend",
    "node": "javascript-backend",
    "aws": "cloud",
    "docker": "containers",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "observability": "observability",
    "otel": "observability",
    "security": "security",
    "oauth": "auth",
    "jwt": "auth",
    "microservice": "microservices",
    "latency": "performance",
    "performance": "performance",
}


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


def _normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in IGNORED_TRACKING_PARAMS
    ]
    normalized_query = urlencode(query_pairs, doseq=True)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            normalized_query,
            "",
        )
    )


def _url_hash(url: str) -> str:
    return hashlib.sha256(_normalize_url(url).encode("utf-8")).hexdigest()


def _extract_rule_tags(title: str, summary: str, category: str) -> list[str]:
    text = f"{title} {summary}".lower()
    tags = set()
    if category:
        tags.add(category.strip().lower())
    for keyword, tag in RULE_TAG_KEYWORDS.items():
        if keyword in text:
            tags.add(tag)
    return sorted(tags)


async def _record_seen_hashes(
    session: AsyncSession,
    feed_id: int,
    hashes: list[str],
    reason_code: str,
) -> None:
    if not hashes:
        return
    now = datetime.now()
    rows = [
        {
            "normalized_url_hash": url_hash,
            "feed_id": feed_id,
            "decision": "duplicate",
            "reason_code": reason_code,
            "first_seen_at": now,
            "last_seen_at": now,
            "seen_count": 1,
        }
        for url_hash in hashes
    ]
    stmt = insert(ArticleDecision).values(rows)
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[ArticleDecision.normalized_url_hash],
            set_={
                "last_seen_at": now,
                "seen_count": ArticleDecision.seen_count + 1,
            },
        )
    )


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
    headers = {
        "User-Agent": settings.http_user_agent,
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
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
        candidates = []
        skipped_hashes = []

        for entry in entries:
            url = entry["url"]
            if not url:
                continue

            normalized_hash = _url_hash(url)
            candidates.append(
                {
                    "article": {
                        "feed_id": feed.id,
                        "title": entry["title"],
                        "url": url,
                        "content": entry["content"],
                        "summary": entry["summary"],
                        "published_at": entry["published_at"],
                    },
                    "url_hash": normalized_hash,
                    "title": entry["title"],
                    "summary": entry["summary"],
                }
            )

        if not candidates:
            feed.last_fetched_at = datetime.now()
            continue

        candidate_hashes = [c["url_hash"] for c in candidates]
        existing_hashes_result = await session.execute(
            select(ArticleDecision.normalized_url_hash).where(
                ArticleDecision.normalized_url_hash.in_(candidate_hashes)
            )
        )
        existing_hashes = set(existing_hashes_result.scalars().all())
        if existing_hashes:
            skipped_hashes = [h for h in candidate_hashes if h in existing_hashes]
            await _record_seen_hashes(
                session=session,
                feed_id=feed.id,
                hashes=skipped_hashes,
                reason_code="seen_again",
            )

        filtered_candidates = [c for c in candidates if c["url_hash"] not in existing_hashes]
        rows_to_insert = [c["article"] for c in filtered_candidates]

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
            inserted_hashes = {_url_hash(row.url) for row in inserted_rows}
            conflict_hashes = [
                c["url_hash"]
                for c in filtered_candidates
                if c["url_hash"] not in inserted_hashes
            ]
            await _record_seen_hashes(
                session=session,
                feed_id=feed.id,
                hashes=conflict_hashes,
                reason_code="article_url_conflict",
            )

            if inserted_rows:
                logger.info(f"AI batch scoring {len(inserted_rows)} articles...")
                article_data = [(row.title, row.summary or "") for row in inserted_rows]
                if settings.groq_api_key:
                    scores = await analyze_articles_batch(article_data)
                else:
                    scores = [0.0] * len(inserted_rows)

                score_rows = []
                tag_rows = []
                decision_rows = []

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
                    score_rows.append(
                        {
                            "article_id": row.id,
                            "relevance_score": score,
                            "backend_depth_score": None,
                            "novelty_score": None,
                            "actionability_score": None,
                            "linkedin_potential_score": None,
                            "final_score": score,
                            "decision": "keep" if is_curated else "discard",
                            "reasoning_summary": (
                                "auto-scored by relevance threshold"
                            ),
                            "scored_at": datetime.now(),
                            "model_name": AI_MODEL_NAME,
                        }
                    )

                    for tag in _extract_rule_tags(
                        title=row.title,
                        summary=row.summary or "",
                        category=feed.category or "",
                    ):
                        tag_rows.append(
                            {
                                "article_id": row.id,
                                "tag": tag,
                                "tag_source": "rule",
                                "created_at": datetime.now(),
                            }
                        )

                    decision_rows.append(
                        {
                            "normalized_url_hash": _url_hash(row.url),
                            "feed_id": feed.id,
                            "article_id": row.id,
                            "decision": "curated" if is_curated else "low_value",
                            "reason_code": "ai_score",
                            "first_seen_at": datetime.now(),
                            "last_seen_at": datetime.now(),
                            "seen_count": 1,
                        }
                    )

                score_insert = insert(ArticleScore).values(score_rows)
                score_excluded = score_insert.excluded
                await session.execute(
                    score_insert.on_conflict_do_update(
                        index_elements=[ArticleScore.article_id],
                        set_={
                            "relevance_score": score_excluded.relevance_score,
                            "backend_depth_score": score_excluded.backend_depth_score,
                            "novelty_score": score_excluded.novelty_score,
                            "actionability_score": score_excluded.actionability_score,
                            "linkedin_potential_score": score_excluded.linkedin_potential_score,
                            "final_score": score_excluded.final_score,
                            "decision": score_excluded.decision,
                            "reasoning_summary": score_excluded.reasoning_summary,
                            "scored_at": score_excluded.scored_at,
                            "model_name": score_excluded.model_name,
                        },
                    )
                )

                if tag_rows:
                    await session.execute(
                        insert(ArticleTag)
                        .values(tag_rows)
                        .on_conflict_do_nothing(
                            index_elements=[
                                ArticleTag.article_id,
                                ArticleTag.tag,
                                ArticleTag.tag_source,
                            ]
                        )
                    )

                decision_insert = insert(ArticleDecision).values(decision_rows)
                decision_excluded = decision_insert.excluded
                await session.execute(
                    decision_insert.on_conflict_do_update(
                        index_elements=[ArticleDecision.normalized_url_hash],
                        set_={
                            "feed_id": decision_excluded.feed_id,
                            "article_id": decision_excluded.article_id,
                            "decision": decision_excluded.decision,
                            "reason_code": decision_excluded.reason_code,
                            "last_seen_at": decision_excluded.last_seen_at,
                            "seen_count": ArticleDecision.seen_count + 1,
                        },
                    )
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


async def cleanup_old_articles(session: AsyncSession) -> dict:
    """Delete old non-curated articles to keep DB growth controlled."""
    cutoff = datetime.now() - timedelta(days=settings.non_curated_retention_days)
    result = await session.execute(
        delete(Article)
        .where(Article.is_curated.is_(False))
        .where(Article.fetched_at < cutoff)
    )
    deleted = result.rowcount or 0
    await session.commit()
    return {
        "deleted_articles": deleted,
        "cutoff": cutoff.isoformat(),
        "retention_days": settings.non_curated_retention_days,
    }
