from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.rss import fetch_all_feeds

router = APIRouter()


@router.post("/fetch/now")
async def trigger_fetch(db: AsyncSession = Depends(get_db)):
    """Manually trigger feed fetching"""
    new_articles = await fetch_all_feeds(db)
    return {"new_articles": new_articles}