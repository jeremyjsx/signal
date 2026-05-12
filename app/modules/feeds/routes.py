from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.feeds.service import (
    cleanup_old_articles,
    create_feed_db,
    fetch_and_review_feeds,
    list_feed_quality_db,
    list_feeds_db,
    list_job_runs_db,
    reactivate_feed_db,
)

router = APIRouter()


class FeedCreate(BaseModel):
    name: str
    url: str
    category: str = ""


@router.post("/feeds/fetch", tags=["feeds"])
async def trigger_fetch(db: AsyncSession = Depends(get_db)):
    """Fetch feeds and auto-score with AI"""
    result = await fetch_and_review_feeds(db)
    return {"new_articles": result}


@router.post("/feeds/cleanup", tags=["feeds"])
async def trigger_cleanup(db: AsyncSession = Depends(get_db)):
    """Delete old non-curated articles based on retention policy."""
    return await cleanup_old_articles(db)


@router.post("/feeds", tags=["feeds"])
async def create_feed(feed: FeedCreate, db: AsyncSession = Depends(get_db)):
    """Create a new feed"""
    return await create_feed_db(feed.name, feed.url, feed.category, db)


@router.post("/feeds/{feed_id}/reactivate", tags=["feeds"])
async def reactivate_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    """Reactivate a feed and reset consecutive failure counters."""
    return await reactivate_feed_db(feed_id=feed_id, db=db)


@router.get("/feeds", tags=["feeds"])
async def list_feeds(db: AsyncSession = Depends(get_db)):
    """List feeds"""
    return await list_feeds_db(db)


@router.get("/feeds/quality", tags=["feeds"])
async def list_feeds_quality(
    status: Optional[str] = Query(default=None),
    min_scored_articles: Optional[int] = Query(default=None, ge=1),
    min_curated_rate: Optional[float] = Query(default=None, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
):
    """List feed quality metrics and health classification."""
    return await list_feed_quality_db(
        db=db,
        status=status,
        min_scored_articles=min_scored_articles,
        min_curated_rate=min_curated_rate,
    )


@router.get("/jobs/runs", tags=["feeds"])
async def list_job_runs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """List recent scheduler runs."""
    return await list_job_runs_db(limit=limit, db=db)