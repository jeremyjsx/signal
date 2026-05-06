from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.articles.service import list_articles_db

router = APIRouter()


@router.get("/articles", tags=["articles"])
async def list_articles(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """List fetched articles"""
    return await list_articles_db(limit, db)
