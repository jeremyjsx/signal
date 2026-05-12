from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.articles.service import list_articles_db, retry_failed_obsidian_exports_db

router = APIRouter()


@router.get("/articles", tags=["articles"])
async def list_articles(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    curated: Optional[bool] = None,
    export_status: Optional[Literal["pending", "exported", "failed"]] = Query(
        default=None
    ),
    score_min: Optional[float] = Query(default=None, ge=0, le=1),
    tag: Optional[str] = Query(default=None),
    order_by: Literal["fetched_at", "score"] = Query(default="fetched_at"),
    order_dir: Literal["asc", "desc"] = Query(default="desc"),
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


@router.post("/articles/obsidian/retry-failed", tags=["articles"])
async def retry_failed_obsidian_exports(
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Move failed Obsidian exports back to pending status."""
    return await retry_failed_obsidian_exports_db(limit=limit, db=db)
