from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.articles.service import list_articles_db

router = APIRouter()


@router.get("/articles", tags=["articles"])
async def list_articles(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    curated: Optional[bool] = None,
    export_status: Optional[str] = Query(default=None),
    score_min: Optional[float] = Query(default=None, ge=0, le=1),
    tag: Optional[str] = Query(default=None),
    order_by: str = Query(default="fetched_at"),
    order_dir: str = Query(default="desc"),
    db: AsyncSession = Depends(get_db),
):
    """List articles with pagination, filters and sorting."""
    return await list_articles_db(
        db=db,
        limit=limit,
        offset=offset,
        curated=curated,
        export_status=export_status,
        score_min=score_min,
        tag=tag,
        order_by=order_by,
        order_dir=order_dir,
    )
