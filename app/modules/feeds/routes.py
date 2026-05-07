from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.feeds.service import create_feed_db, fetch_and_review_feeds, list_feeds_db

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


@router.post("/feeds", tags=["feeds"])
async def create_feed(feed: FeedCreate, db: AsyncSession = Depends(get_db)):
    """Create a new feed"""
    return await create_feed_db(feed.name, feed.url, feed.category, db)


@router.get("/feeds", tags=["feeds"])
async def list_feeds(db: AsyncSession = Depends(get_db)):
    """List feeds"""
    return await list_feeds_db(db)